import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Execution, PerformanceSnapshot, RiskDecision, Signal, TradeIntent


@dataclass
class RiskResult:
    verdict: str
    reasons: list[str]
    approved_size: float
    requested_size: float


def _latest_performance(db: Session) -> PerformanceSnapshot | None:
    q = select(PerformanceSnapshot).order_by(desc(PerformanceSnapshot.timestamp)).limit(1)
    return db.execute(q).scalar_one_or_none()


def _duplicate_recent(db: Session, signal: Signal, window_minutes: int = 30) -> bool:
    """Churn guard: repeat *filled* same-direction lane/core trades only (blocks/reviews do not consume the window)."""
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    q = (
        select(TradeIntent)
        .join(Execution, Execution.intent_id == TradeIntent.id)
        .where(
            TradeIntent.asset == signal.asset,
            TradeIntent.created_at >= since,
            Execution.status == "filled",
        )
        .order_by(desc(TradeIntent.created_at))
        .limit(8)
    )
    for intent in db.execute(q).scalars().all():
        if intent.signal_id is None:
            continue
        prev_sig = db.get(Signal, intent.signal_id)
        if prev_sig and prev_sig.signal_type == signal.signal_type:
            return True
    return False


def evaluate_signal(
    db: Session,
    signal: Signal,
    requested_notional: float,
    snapshot_captured_at: datetime,
    volatility_flag: bool,
    manual_pause: bool,
    no_trade: bool,
    *,
    duplicate_window_minutes: int | None = None,
) -> RiskResult:
    settings = get_settings()
    reasons: list[str] = []
    req = requested_notional
    approved = req
    verdict = "allow"

    if manual_pause:
        return RiskResult("block", ["manual_pause"], 0.0, req)
    if no_trade:
        return RiskResult("block", ["no_trade_state"], 0.0, req)

    cap = snapshot_captured_at
    if cap.tzinfo is not None:
        cap = cap.replace(tzinfo=None)
    age = datetime.utcnow() - cap
    if age > timedelta(seconds=120):
        return RiskResult("block", ["stale_market_data"], 0.0, req)

    if volatility_flag:
        return RiskResult("block", ["volatility_anomaly"], 0.0, req)

    if signal.signal_type == "hold":
        return RiskResult("skip", ["signal_hold_no_action"], 0.0, req)

    if signal.confidence < settings.default_confidence_threshold:
        return RiskResult("escalate_for_review", ["confidence_below_threshold"], 0.0, req)

    perf = _latest_performance(db)
    if perf:
        if perf.drawdown >= settings.default_max_drawdown:
            return RiskResult("block", ["max_drawdown_exceeded"], 0.0, req)
        if perf.pnl_daily <= -settings.default_max_daily_loss:
            return RiskResult("block", ["max_daily_loss_exceeded"], 0.0, req)
        if signal.signal_type == "sell":
            room = max(0.0, float(perf.position_notional or 0.0))
        else:
            room = max(0.0, settings.default_max_position_notional - float(perf.position_notional or 0.0))
        if req > room:
            if room <= 0:
                return RiskResult("block", ["max_position_notional"], 0.0, req)
            approved = room
            verdict = "allow_with_reduction"
            reasons.append(
                "reduced_to_open_position" if signal.signal_type == "sell" else "reduced_to_max_position_notional"
            )

    dup_win = int(duplicate_window_minutes) if duplicate_window_minutes is not None else 30
    dup_win = max(1, min(120, dup_win))
    if _duplicate_recent(db, signal, window_minutes=dup_win):
        return RiskResult("block", ["duplicate_action"], 0.0, req)

    if verdict == "allow":
        reasons.append("policy_ok")
    return RiskResult(verdict, reasons, approved, req)


def persist_risk_decision(
    db: Session,
    signal: Signal,
    result: RiskResult,
    policy_version: str,
) -> RiskDecision:
    row = RiskDecision(
        related_signal_id=signal.id,
        timestamp=datetime.utcnow(),
        verdict=result.verdict,
        reasons=json.dumps(result.reasons),
        policy_version=policy_version,
        approved_size=result.approved_size,
        requested_size=result.requested_size,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
