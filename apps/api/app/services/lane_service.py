from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Execution,
    LanePerformanceSnapshot,
    MarketSnapshot,
    RiskDecision,
    Signal,
    TradeIntent,
    TradingLaneState,
)
from app.services import artifact_service, candle_service, execution_service, intent_service, market_service, risk_engine

LANE_DEFS = {
    "spot_momentum": {
        "lane_label": "Spot Momentum",
        "market_type": "spot",
        "strategy_family": "momentum",
        "default_symbols": ["BTCUSD", "ETHUSD", "SOLUSD"],
        "capital_allocation": 7000.0,
        "risk_profile": "safer_spot",
        "cadence_seconds": 15,
    },
    "futures_tactical": {
        "lane_label": "Futures Tactical",
        "market_type": "futures_paper",
        "strategy_family": "tactical",
        "default_symbols": ["BTCUSD"],
        "capital_allocation": 3000.0,
        "risk_profile": "tighter_high_upside",
        "cadence_seconds": 30,
    },
}


@dataclass
class LaneRiskPolicy:
    confidence_threshold: float
    max_position_notional: float
    max_daily_loss: float
    max_drawdown: float
    severe_vol_block: bool


def _policy_for_lane(lane_id: str) -> LaneRiskPolicy:
    s = get_settings()
    if lane_id == "futures_tactical":
        # Tactical lane stays stricter than spot; threshold tuned so marginal tape maps to trim/skip—not review spam.
        return LaneRiskPolicy(
            confidence_threshold=max(0.62, s.default_confidence_threshold + 0.045),
            max_position_notional=min(250.0, s.default_max_position_notional * 0.55),
            max_daily_loss=min(120.0, s.default_max_daily_loss * 0.5),
            max_drawdown=min(260.0, s.default_max_drawdown * 0.55),
            severe_vol_block=True,
        )
    return LaneRiskPolicy(
        confidence_threshold=s.default_confidence_threshold,
        max_position_notional=s.default_max_position_notional,
        max_daily_loss=s.default_max_daily_loss,
        max_drawdown=s.default_max_drawdown,
        severe_vol_block=True,
    )


def _ensure_lanes(db: Session) -> None:
    changed = False
    for lane_id, cfg in LANE_DEFS.items():
        row = db.execute(select(TradingLaneState).where(TradingLaneState.lane_id == lane_id)).scalar_one_or_none()
        if row is None:
            row = TradingLaneState(
                lane_id=lane_id,
                lane_label=cfg["lane_label"],
                market_type=cfg["market_type"],
                strategy_family=cfg["strategy_family"],
                default_symbols_json=json.dumps(cfg["default_symbols"]),
                capital_allocation=cfg["capital_allocation"],
                risk_profile=cfg["risk_profile"],
                cadence_seconds=cfg["cadence_seconds"],
                status="stopped",
                last_outcome="idle",
            )
            db.add(row)
            changed = True
    if changed:
        db.commit()


def _symbols(row: TradingLaneState) -> list[str]:
    try:
        parsed = json.loads(row.default_symbols_json or "[]")
        if isinstance(parsed, list) and parsed:
            return [str(x).upper() for x in parsed]
    except json.JSONDecodeError:
        pass
    return ["BTCUSD"]


def _latest_lane_perf(db: Session, lane_id: str) -> LanePerformanceSnapshot | None:
    q = (
        select(LanePerformanceSnapshot)
        .where(LanePerformanceSnapshot.lane_id == lane_id)
        .order_by(desc(LanePerformanceSnapshot.timestamp))
        .limit(1)
    )
    return db.execute(q).scalar_one_or_none()


def _seed_lane_perf(db: Session, lane: TradingLaneState) -> LanePerformanceSnapshot:
    row = LanePerformanceSnapshot(
        lane_id=lane.lane_id,
        timestamp=datetime.utcnow(),
        equity=lane.capital_allocation,
        pnl_daily=0.0,
        pnl_total=0.0,
        drawdown=0.0,
        open_notional=0.0,
        turnover=0.0,
        allow_count=0,
        reduce_count=0,
        block_count=0,
        skip_count=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _std_last_n(closes: list[float], n: int) -> float:
    tail = closes[-n:] if len(closes) >= n else closes
    if len(tail) < 2:
        return 0.0
    return float(statistics.pstdev(tail))


def _last_lane_buy_fill(db: Session, lane_id: str) -> tuple[datetime, float] | None:
    """Latest filled lane buy: (execution time, entry price)."""
    q = (
        select(Execution)
        .join(TradeIntent, TradeIntent.id == Execution.intent_id)
        .where(
            Execution.lane_id == lane_id,
            Execution.status == "filled",
            TradeIntent.action == "buy",
            TradeIntent.lane_id == lane_id,
        )
        .order_by(desc(Execution.created_at))
        .limit(1)
    )
    ex = db.execute(q).scalar_one_or_none()
    if ex is None or ex.fill_price is None:
        return None
    cap = ex.created_at
    if cap.tzinfo is not None:
        cap = cap.replace(tzinfo=None)
    return cap, float(ex.fill_price)


def _recent_prices(db: Session, symbol: str, limit: int = 6) -> list[float]:
    q = (
        select(MarketSnapshot.price)
        .where(MarketSnapshot.symbol == symbol)
        .order_by(desc(MarketSnapshot.captured_at))
        .limit(limit)
    )
    return list(db.execute(q).scalars().all())


def _lane_signal(db: Session, lane: TradingLaneState, snapshot: MarketSnapshot) -> Signal:
    sym = snapshot.symbol
    closes = candle_service.recent_close_prices(db, sym, n=80)
    perf = _latest_lane_perf(db, lane.lane_id)
    p = _policy_for_lane(lane.lane_id)

    def _from_snapshots() -> tuple[str, float, str, str]:
        prices = _recent_prices(db, sym, limit=6)
        short = prices[0] if prices else snapshot.price
        long = sum(prices) / len(prices) if prices else snapshot.price
        momentum = (short / long - 1.0) if long else 0.0
        if lane.lane_id == "futures_tactical":
            th = 0.0022
            conf = min(0.97, 0.62 + abs(momentum) * 105.0)
            if abs(momentum) < th:
                return "hold", min(0.54, 0.48 + abs(momentum) * 120.0), (
                    f"Tactical futures (tape fallback): bias={momentum:.4%} vs trigger {th:.2%}; waiting for clearer impulse."
                ), "futures_tactical_momentum"
            st = "buy" if momentum > 0 else "sell"
            return st, conf, (
                f"Tactical futures (tape fallback): bias={momentum:.4%} vs trigger {th:.2%}; directional impulse present."
            ), "futures_tactical_momentum"
        th = 0.0015
        conf = min(0.93, 0.56 + abs(momentum) * 75.0)
        st = "buy" if momentum >= -th else "sell"
        return st, conf, (
            f"Spot momentum (tape fallback): micro-trend delta={momentum:.4%} vs band ±{th:.2%}."
        ), "spot_momentum_continuation"

    if perf is not None and perf.open_notional >= p.max_position_notional * 0.42:
        signal_type = "sell"
        confidence = min(0.9, 0.64 + (perf.open_notional / max(p.max_position_notional, 1.0)) * 0.1)
        rationale = (
            f"{lane.lane_label}: inventory-led unwind — open_notional≈{perf.open_notional:.0f} vs cap {p.max_position_notional:.0f} "
            "(paper ledger trim so the lane can cycle without sitting on max exposure)."
        )
        strategy_id = "futures_tactical_momentum" if lane.lane_id == "futures_tactical" else "spot_momentum_continuation"
    elif len(closes) < 22:
        signal_type, confidence, rationale, strategy_id = _from_snapshots()
    else:
        w_short = min(10, len(closes))
        w_long = min(40, len(closes))
        short_ma = sum(closes[-w_short:]) / w_short
        long_ma = sum(closes[-w_long:]) / w_long
        spread = (short_ma / long_ma - 1.0) if long_ma else 0.0
        look_m = min(12, len(closes) - 1)
        mom_bar = (closes[-1] - closes[-look_m - 1]) / abs(closes[-look_m - 1]) if closes[-look_m - 1] else 0.0
        up = sum(1 for i in range(1, min(5, len(closes))) if closes[-i] > closes[-i - 1])
        persist = up / max(1, min(4, len(closes) - 1))

        if lane.lane_id == "futures_tactical":
            th = 0.00055
            brk = max(0.00025, _std_last_n(closes, 8) * 1.15 / (closes[-1] or 1.0))
            need = max(th, brk)
            confidence = min(0.97, 0.62 + min(0.28, abs(spread) * 900.0 + abs(mom_bar) * 2.2 + persist * 0.06))
            if abs(spread) < need or abs(mom_bar) < 0.00012:
                signal_type = "hold"
                rationale = (
                    f"Tactical futures: 1m MA{w_short}/MA{w_long} spread {spread:.4%}, ~{look_m}m return {mom_bar:.4%}, "
                    f"persistence={persist:.2f}; need spread≥{need:.4%} and non-flat drift — no tactical entry."
                )
            elif spread > 0 and mom_bar >= -0.0002:
                signal_type = "buy"
                rationale = (
                    f"Tactical futures: bullish alignment (spread {spread:.4%}, return {mom_bar:.4%}, persistence {persist:.2f})."
                )
            elif spread < 0 and mom_bar <= 0.0002:
                signal_type = "sell"
                rationale = (
                    f"Tactical futures: bearish alignment (spread {spread:.4%}, return {mom_bar:.4%}, persistence {persist:.2f})."
                )
            else:
                signal_type = "hold"
                rationale = (
                    f"Tactical futures: mixed tape (spread {spread:.4%} vs return {mom_bar:.4%}) — skip chop."
                )
            strategy_id = "futures_tactical_momentum"
        else:
            th = 0.00032
            confidence = min(0.92, 0.57 + min(0.3, abs(spread) * 720.0 + abs(mom_bar) * 1.8 + persist * 0.05))
            inv_cap = p.max_position_notional * 0.5
            flatten = perf is not None and perf.open_notional >= inv_cap
            if flatten and spread <= th * 1.8:
                signal_type = "sell"
                confidence = min(0.9, 0.62 + min(0.22, (perf.open_notional / max(p.max_position_notional, 1.0)) * 0.12))
                rationale = (
                    f"Spot momentum: inventory trim — open_notional≈{perf.open_notional:.0f} vs cap {p.max_position_notional:.0f}; "
                    f"spread {spread:.4%} no longer supportive of adding size."
                )
            elif spread > th and mom_bar > -0.00025 and persist >= 0.25:
                signal_type = "buy"
                rationale = (
                    f"Spot momentum: MA{w_short}>MA{w_long} by {spread:.4%}, ~{look_m}m return {mom_bar:.4%}, "
                    f"directional persistence {persist:.2f}."
                )
            elif spread < -th and mom_bar < 0.00025 and persist <= 0.75:
                signal_type = "sell"
                rationale = (
                    f"Spot momentum: MA{w_short}<MA{w_long} by {abs(spread):.4%}, ~{look_m}m return {mom_bar:.4%}, "
                    f"persistence {persist:.2f}."
                )
            else:
                signal_type = "hold"
                rationale = (
                    f"Spot momentum: spread {spread:.4%} inside noise band ±{th:.4%} or momentum/persistence weak — stand aside."
                )
            strategy_id = "spot_momentum_continuation"

    # Tactical exits (futures): stop / take-profit / short max-hold on paper ledger.
    entry_ft = _last_lane_buy_fill(db, lane.lane_id)
    if lane.lane_id == "futures_tactical" and entry_ft and perf and perf.open_notional >= 12.0:
        dt_e, epx = entry_ft
        age_min = (datetime.utcnow() - dt_e).total_seconds() / 60.0
        px = float(closes[-1]) if closes else float(snapshot.price)
        ret = (px - epx) / epx if epx else 0.0
        if ret <= -0.0018:
            signal_type, confidence = "sell", min(0.92, 0.68 + abs(ret) * 45.0)
            rationale = f"Tactical futures: stop-out (~{ret * 100:.3f}% vs entry {epx:.2f})."
            strategy_id = "futures_tactical_momentum"
        elif ret >= 0.0026:
            signal_type, confidence = "sell", min(0.93, 0.7 + min(0.22, ret * 35.0))
            rationale = f"Tactical futures: take-profit (~{ret * 100:.3f}% vs entry {epx:.2f})."
            strategy_id = "futures_tactical_momentum"
        elif age_min >= 5.2:
            signal_type, confidence = "sell", min(0.9, 0.65 + min(0.2, age_min / 45.0))
            rationale = f"Tactical futures: time stop (~{age_min:.0f}m in clip) — tactical lane folds fast."
            strategy_id = "futures_tactical_momentum"

    # Spot exits: trend-fade + max hold (paper ledger).
    if lane.lane_id == "spot_momentum" and len(closes) >= 22 and perf and perf.open_notional >= p.max_position_notional * 0.06:
        w_s = min(10, len(closes))
        short_ma = sum(closes[-w_s:]) / w_s
        lag_ma = sum(closes[-w_s - 5 : -5]) / w_s if len(closes) >= w_s + 6 else short_ma
        if short_ma < lag_ma * 0.99978 and signal_type in ("buy", "hold"):
            signal_type = "sell"
            confidence = min(0.9, 0.64 + (perf.open_notional / max(p.max_position_notional, 1.0)) * 0.1)
            rationale = (
                f"Spot momentum: trend-fade exit — MA{w_s} slope rolled vs prior band while inventory ≈{perf.open_notional:.0f}."
            )
            strategy_id = "spot_momentum_continuation"
        else:
            entry_sp = _last_lane_buy_fill(db, lane.lane_id)
            if entry_sp and signal_type in ("buy", "hold"):
                dt_s, _epx = entry_sp
                age_sp = (datetime.utcnow() - dt_s).total_seconds() / 60.0
                if age_sp >= 17.0:
                    signal_type = "sell"
                    confidence = min(0.88, 0.63 + min(0.2, age_sp / 120.0))
                    rationale = f"Spot momentum: max-hold ~{age_sp:.0f}m — flatten so exposure does not drift."
                    strategy_id = "spot_momentum_continuation"

    if lane.lane_id == "spot_momentum" and signal_type == "buy" and perf is not None:
        inv_soft = p.max_position_notional * 0.72
        if perf.open_notional >= inv_soft:
            signal_type = "hold"
            confidence = min(confidence, 0.54)
            rationale += (
                f" Size gate: open_notional {perf.open_notional:.0f} near lane cap {p.max_position_notional:.0f} — wait for exit/trim."
            )
    sig = Signal(
        asset=snapshot.symbol,
        timestamp=datetime.utcnow(),
        signal_type=signal_type,
        confidence=float(round(confidence, 4)),
        rationale=rationale,
        strategy_id=strategy_id,
        market_snapshot_id=snapshot.id,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


def _lane_risk(
    db: Session,
    lane: TradingLaneState,
    signal: Signal,
    requested_notional: float,
    snapshot: MarketSnapshot,
    manual_pause: bool,
    no_trade: bool,
) -> risk_engine.RiskResult:
    base = risk_engine.evaluate_signal(
        db,
        signal,
        requested_notional,
        snapshot.captured_at,
        snapshot.volatility_flag,
        manual_pause,
        no_trade,
        duplicate_window_minutes=2,
    )
    p = _policy_for_lane(lane.lane_id)
    # Honor global halt outcomes before lane overlays (and do not turn holds into review noise).
    if signal.signal_type == "hold" or base.verdict in {"block", "skip"}:
        return base

    perf = _latest_lane_perf(db, lane.lane_id) or _seed_lane_perf(db, lane)
    if perf.drawdown >= p.max_drawdown:
        return risk_engine.RiskResult("block", ["lane_max_drawdown_exceeded"], 0.0, requested_notional)
    if perf.pnl_daily <= -p.max_daily_loss:
        return risk_engine.RiskResult("block", ["lane_max_daily_loss_exceeded"], 0.0, requested_notional)
    if perf.open_notional >= p.max_position_notional and signal.signal_type == "buy":
        return risk_engine.RiskResult("block", ["lane_max_open_notional"], 0.0, requested_notional)

    if signal.confidence < p.confidence_threshold:
        gap = p.confidence_threshold - signal.confidence
        if lane.lane_id == "futures_tactical" and signal.signal_type in {"buy", "sell"}:
            if gap <= 0.14:
                clip = min(requested_notional * 0.48, p.max_position_notional * 0.5)
                if clip >= 26.0:
                    return risk_engine.RiskResult(
                        "allow_with_reduction",
                        ["lane_soft_conviction_trim", "lane_size_reduction"],
                        clip,
                        requested_notional,
                    )
            if gap <= 0.175:
                return risk_engine.RiskResult(
                    "skip",
                    ["lane_futures_marginal_conviction"],
                    0.0,
                    requested_notional,
                )
        if lane.lane_id == "spot_momentum" and signal.signal_type in {"buy", "sell"} and gap <= 0.055:
            return risk_engine.RiskResult(
                "skip",
                ["lane_spot_marginal_conviction"],
                0.0,
                requested_notional,
            )
        return risk_engine.RiskResult("escalate_for_review", ["lane_confidence_gate"], 0.0, requested_notional)
    if requested_notional > p.max_position_notional:
        return risk_engine.RiskResult("allow_with_reduction", ["lane_size_reduction"], p.max_position_notional, requested_notional)
    return base


def _update_lane_perf(db: Session, lane: TradingLaneState, ex: Execution | None, verdict: str) -> LanePerformanceSnapshot:
    prev = _latest_lane_perf(db, lane.lane_id) or _seed_lane_perf(db, lane)
    allow_count = prev.allow_count + (1 if verdict == "allow" else 0)
    reduce_count = prev.reduce_count + (1 if verdict == "allow_with_reduction" else 0)
    block_count = prev.block_count + (1 if verdict in {"block", "escalate_for_review"} else 0)
    skip_count = int(getattr(prev, "skip_count", 0) or 0) + (1 if verdict == "skip" else 0)
    open_notional = prev.open_notional
    pnl_delta = 0.0
    turnover = prev.turnover
    if ex and ex.status == "filled" and ex.fill_price and ex.fill_size:
        notional = ex.fill_price * ex.fill_size
        turnover += notional
        intent = db.get(TradeIntent, ex.intent_id)
        side = (intent.action.lower() if intent else "buy")
        open_notional = max(0.0, open_notional + (notional if side == "buy" else -notional))
        pnl_delta = -float(ex.fees or 0.0)
    equity = prev.equity + pnl_delta
    peak = max(prev.equity, equity, lane.capital_allocation)
    drawdown = max(0.0, peak - equity)
    row = LanePerformanceSnapshot(
        lane_id=lane.lane_id,
        timestamp=datetime.utcnow(),
        equity=round(equity, 4),
        pnl_daily=round(pnl_delta, 4),
        pnl_total=round(equity - lane.capital_allocation, 4),
        drawdown=round(drawdown, 4),
        open_notional=round(open_notional, 4),
        turnover=round(turnover, 4),
        allow_count=allow_count,
        reduce_count=reduce_count,
        block_count=block_count,
        skip_count=skip_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_lanes(db: Session) -> list[dict]:
    _ensure_lanes(db)
    rows = db.execute(select(TradingLaneState).order_by(TradingLaneState.lane_id)).scalars().all()
    out: list[dict] = []
    for r in rows:
        perf = _latest_lane_perf(db, r.lane_id) or _seed_lane_perf(db, r)
        out.append(
            {
                "lane_id": r.lane_id,
                "lane_label": r.lane_label,
                "market_type": r.market_type,
                "strategy_family": r.strategy_family,
                "default_symbols": _symbols(r),
                "capital_allocation": r.capital_allocation,
                "risk_profile": r.risk_profile,
                "cadence_seconds": r.cadence_seconds,
                "status": r.status,
                "last_outcome": r.last_outcome,
                "performance": {
                    "equity": perf.equity,
                    "pnl_total": perf.pnl_total,
                    "drawdown": perf.drawdown,
                    "open_notional": perf.open_notional,
                    "allow_count": perf.allow_count,
                    "reduce_count": perf.reduce_count,
                    "block_count": perf.block_count,
                    "skip_count": int(getattr(perf, "skip_count", 0) or 0),
                },
            }
        )
    return out


def get_lane(db: Session, lane_id: str) -> dict | None:
    for lane in list_lanes(db):
        if lane["lane_id"] == lane_id:
            return lane
    return None


def get_lane_history(db: Session, lane_id: str, limit: int = 30) -> list[dict]:
    q = (
        select(TradeIntent)
        .where(TradeIntent.lane_id == lane_id)
        .order_by(desc(TradeIntent.created_at))
        .limit(min(max(limit, 1), 200))
    )
    rows = db.execute(q).scalars().all()
    return [
        {
            "intent_id": r.id,
            "created_at": r.created_at,
            "asset": r.asset,
            "action": r.action,
            "requested_size": r.requested_size,
            "approved_size": r.approved_size,
            "risk_verdict": r.risk_verdict,
            "rationale": r.rationale,
            "status": r.status,
        }
        for r in rows
    ]


def get_lane_performance(db: Session, lane_id: str, limit: int = 60) -> list[dict]:
    q = (
        select(LanePerformanceSnapshot)
        .where(LanePerformanceSnapshot.lane_id == lane_id)
        .order_by(desc(LanePerformanceSnapshot.timestamp))
        .limit(min(max(limit, 1), 300))
    )
    rows = db.execute(q).scalars().all()
    return [
        {
            "timestamp": r.timestamp,
            "equity": r.equity,
            "pnl_daily": r.pnl_daily,
            "pnl_total": r.pnl_total,
            "drawdown": r.drawdown,
            "open_notional": r.open_notional,
            "turnover": r.turnover,
            "allow_count": r.allow_count,
            "reduce_count": r.reduce_count,
            "block_count": r.block_count,
            "skip_count": int(getattr(r, "skip_count", 0) or 0),
        }
        for r in rows
    ]


def set_lane_status(db: Session, lane_id: str, status: str) -> dict | None:
    _ensure_lanes(db)
    row = db.execute(select(TradingLaneState).where(TradingLaneState.lane_id == lane_id)).scalar_one_or_none()
    if row is None:
        return None
    row.status = status
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    return get_lane(db, lane_id)


def run_lane_once(db: Session, lane_id: str) -> dict:
    _ensure_lanes(db)
    lane = db.execute(select(TradingLaneState).where(TradingLaneState.lane_id == lane_id)).scalar_one_or_none()
    if lane is None:
        return {"ok": False, "error": "lane_not_found"}
    symbols = _symbols(lane)
    snapshot = market_service.ingest_for_settings(db)
    if snapshot.symbol not in symbols:
        snapshot = market_service.ingest_mock_snapshot(db, symbol=symbols[0], source_override=snapshot.source)
    candle_service.refresh_candles_for_symbol(db, snapshot.symbol, target_bars=360)
    signal = _lane_signal(db, lane, snapshot)
    requested = min(lane.capital_allocation * 0.2, _policy_for_lane(lane_id).max_position_notional * 1.2)
    risk = _lane_risk(db, lane, signal, requested, snapshot, manual_pause=False, no_trade=False)
    risk_row = risk_engine.persist_risk_decision(db, signal, risk, get_settings().policy_version)
    artifact_service.write_artifact(
        db,
        "lane_signal",
        str(signal.id),
        {
            "lane_id": lane.lane_id,
            "lane_label": lane.lane_label,
            "signal_type": signal.signal_type,
            "confidence": signal.confidence,
            "rationale": signal.rationale,
        },
    )
    artifact_service.write_artifact(
        db,
        "lane_risk",
        str(risk_row.id),
        {"lane_id": lane.lane_id, "verdict": risk.verdict, "reasons": risk.reasons, "approved_notional": risk.approved_size},
    )
    if risk.verdict in {"block", "escalate_for_review"}:
        perf = _update_lane_perf(db, lane, None, risk.verdict)
        lane.last_outcome = risk.verdict
        db.add(lane)
        db.commit()
        return {
            "ok": True,
            "lane_id": lane_id,
            "lane_label": lane.lane_label,
            "blocked": risk.verdict == "block",
            "escalated": risk.verdict == "escalate_for_review",
            "verdict": risk.verdict,
            "lane_performance": {"equity": perf.equity, "pnl_total": perf.pnl_total},
        }

    if risk.verdict == "skip":
        perf = _update_lane_perf(db, lane, None, risk.verdict)
        lane.last_outcome = "skip"
        db.add(lane)
        db.commit()
        return {
            "ok": True,
            "lane_id": lane_id,
            "lane_label": lane.lane_label,
            "blocked": False,
            "skipped": True,
            "escalated": False,
            "verdict": risk.verdict,
            "lane_performance": {
                "equity": perf.equity,
                "pnl_total": perf.pnl_total,
                "skip_count": int(getattr(perf, "skip_count", 0) or 0),
            },
        }

    intent = intent_service.create_intent(
        db,
        asset=signal.asset,
        action=signal.signal_type,
        requested_size=risk.requested_size,
        approved_size=risk.approved_size,
        rationale=(
            f"{lane.lane_label} proposed {signal.signal_type}: "
            f"{signal.rationale} Risk verdict={risk.verdict}. "
            "Explanation: trade entered because lane signal passed threshold; "
            "exit/continuation is policy-bound in paper mode."
        ),
        confidence=signal.confidence,
        strategy_id=signal.strategy_id,
        policy_version=get_settings().policy_version,
        risk_verdict=risk.verdict,
        signal_id=signal.id,
        risk_decision_id=risk_row.id,
        status="approved",
        lane_id=lane.lane_id,
        lane_label=lane.lane_label,
        market_type=lane.market_type,
        strategy_family=lane.strategy_family,
        capital_bucket=lane.capital_allocation,
    )
    ex = execution_service.simulate_execution(db, intent, snapshot.price)
    ex.lane_id = lane.lane_id
    ex.market_type = lane.market_type
    ex.strategy_family = lane.strategy_family
    db.add(ex)
    db.commit()
    db.refresh(ex)
    artifact_service.write_artifact(
        db,
        "lane_execution",
        str(ex.id),
        {
            "lane_id": lane.lane_id,
            "status": ex.status,
            "entry_reason": f"{lane.lane_label} entered due to lane signal and confidence.",
            "exit_reason": "Paper simulator: market intent filled at snapshot price; lane PnL updates from fees and open-notional ledger (not a venue-held position).",
            "blocked_or_reduced_reason": (
                "Futures lane: soft conviction trim then capped notional."
                if risk.verdict == "allow_with_reduction" and "lane_soft_conviction_trim" in risk.reasons
                else "Size reduced by lane policy."
                if risk.verdict == "allow_with_reduction"
                else "N/A"
            ),
            "market_context": f"{snapshot.symbol} @ {snapshot.price}",
            "session_outcome": ex.message,
        },
    )
    perf = _update_lane_perf(db, lane, ex, risk.verdict)
    lane.last_outcome = risk.verdict
    db.add(lane)
    db.commit()
    return {
        "ok": True,
        "lane_id": lane_id,
        "lane_label": lane.lane_label,
        "verdict": risk.verdict,
        "intent_id": intent.id,
        "execution_id": ex.id,
        "execution_status": ex.status,
        "lane_performance": {"equity": perf.equity, "pnl_total": perf.pnl_total},
    }
