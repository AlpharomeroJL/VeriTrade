"""Chart + session aggregates for operator visualization — read-only, no new infra."""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Execution, MarketSnapshot, RiskDecision, Signal, TradeIntent
from app.services import candle_service


def snapshot_price_for_signal(db: Session, signal_id: int | None) -> float | None:
    if signal_id is None:
        return None
    sig = db.get(Signal, signal_id)
    if sig is None or sig.market_snapshot_id is None:
        return None
    snap = db.get(MarketSnapshot, sig.market_snapshot_id)
    return float(snap.price) if snap else None


def market_price_series(db: Session, symbol: str, limit: int) -> list[dict]:
    sym = symbol.upper()
    lim = max(10, min(500, limit))
    q = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == sym)
        .order_by(MarketSnapshot.captured_at.desc())
        .limit(lim)
    )
    rows = list(db.execute(q).scalars().all())
    rows.reverse()
    return [{"t": r.captured_at, "price": float(r.price)} for r in rows]


def trade_markers_for_chart(db: Session, symbol: str, limit: int) -> list[dict]:
    """Map recent intents to chart markers (buy / sell / blocked / reduced / review)."""
    sym = symbol.upper()
    lim = max(5, min(60, limit))
    q = (
        select(TradeIntent)
        .where(TradeIntent.asset == sym)
        .order_by(TradeIntent.created_at.desc())
        .limit(lim)
    )
    intents = list(db.execute(q).scalars().all())
    out: list[dict] = []
    for intent in intents:
        if intent.action == "hold":
            continue
        risk_row = db.get(RiskDecision, intent.risk_decision_id) if intent.risk_decision_id else None
        ex = db.execute(
            select(Execution)
            .where(Execution.intent_id == intent.id)
            .order_by(Execution.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        price = None
        if ex and ex.fill_price is not None:
            price = float(ex.fill_price)
        if price is None:
            p = snapshot_price_for_signal(db, intent.signal_id)
            price = float(p) if p is not None else None
        if price is None:
            continue

        ts = intent.created_at
        if ex and ex.status == "filled":
            ts = ex.created_at
        elif risk_row is not None:
            ts = risk_row.timestamp

        verdict = intent.risk_verdict or ""
        if verdict == "block":
            kind = "blocked"
            label = f"Blocked: {intent.action} {intent.asset}"
        elif verdict == "escalate_for_review":
            kind = "review"
            label = f"Review: {intent.action} {intent.asset}"
        elif ex and ex.status == "filled":
            if verdict == "allow_with_reduction":
                kind = "reduced"
                label = f"Trimmed then filled: {intent.action} {intent.asset}"
            elif intent.action == "sell":
                kind = "sell"
                label = f"Paper sell @ {price:.2f}"
            else:
                kind = "buy"
                label = f"Paper buy @ {price:.2f}"
        else:
            continue

        out.append({"ts": ts, "price": price, "kind": kind, "label": label})
    out.sort(key=lambda x: x["ts"])
    return out


def market_chart_pack_data(
    db: Session, symbol: str, limit: int, *, interval_minutes: int = 1, interval_code: str = "1m"
) -> dict:
    """OHLC candles + legacy close line + markers + plain-English market context."""
    sym = symbol.upper()
    lim = max(120, min(720, int(limit)))
    candles, points, src = candle_service.candles_for_chart_pack(db, sym, lim, interval_minutes=interval_minutes)
    markers = trade_markers_for_chart(db, sym, 60)
    ctx = candle_service.build_market_context_dict(candles, source_hint=src, interval_minutes=interval_minutes)
    last_risk = db.execute(select(RiskDecision).order_by(desc(RiskDecision.timestamp)).limit(1)).scalar_one_or_none()
    verdict = last_risk.verdict if last_risk else None
    ctx_out = None
    if ctx:
        ctx_out = {**ctx, "trade_hint": candle_service.plain_allow_block_hint(ctx, verdict)}
    return {
        "symbol": sym,
        "interval": interval_code,
        "candles": candles,
        "points": points,
        "markers": markers,
        "context": ctx_out,
    }


def paper_session_summary(db: Session) -> dict:
    """Aggregate paper session stats for long-running demos (same DB)."""
    filled = int(
        db.scalar(select(func.count()).select_from(Execution).where(Execution.status == "filled")) or 0
    )
    blocked = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "block")) or 0
    )
    skipped = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "skip")) or 0
    )
    reduced = int(
        db.scalar(
            select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "allow_with_reduction")
        )
        or 0
    )
    review = int(
        db.scalar(
            select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "escalate_for_review")
        )
        or 0
    )
    allow_full = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "allow")) or 0
    )

    best_ex = db.execute(
        select(Execution)
        .where(Execution.status == "filled", Execution.fill_size.is_not(None))
        .order_by(Execution.fill_size.desc())
        .limit(1)
    ).scalar_one_or_none()
    worst_ex = db.execute(
        select(Execution)
        .where(Execution.status == "rejected")
        .order_by(Execution.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    best_label = None
    if best_ex and best_ex.fill_size:
        intent = db.get(TradeIntent, best_ex.intent_id)
        a = intent.asset if intent else "—"
        act = intent.action if intent else "—"
        best_label = f"Largest simulated fill: {act} {a}, size {float(best_ex.fill_size):.2f}"

    worst_label = None
    if worst_ex:
        intent = db.get(TradeIntent, worst_ex.intent_id)
        a = intent.asset if intent else "—"
        worst_label = f"Recent paper rejection on {a} — {worst_ex.message[:80] if worst_ex.message else 'no fill'}"

    parts = []
    if filled:
        parts.append(f"{filled} simulated fill{'s' if filled != 1 else ''}")
    if skipped:
        parts.append(f"{skipped} stand-aside{'s' if skipped != 1 else ''} (no trade)")
    if blocked:
        parts.append(f"{blocked} hard block{'s' if blocked != 1 else ''} at risk")
    if reduced:
        parts.append(f"{reduced} size trim{'s' if reduced != 1 else ''}")
    if review:
        parts.append(f"{review} sent for review")
    story = (
        "Session so far: " + ", ".join(parts) + "."
        if parts
        else "Session so far: run demo seed and cycles to build a visible story on the chart."
    )

    return {
        "filled_trades": filled,
        "blocked": blocked,
        "skipped": skipped,
        "reduced": reduced,
        "review": review,
        "allow_full": allow_full,
        "best_win_label": best_label,
        "worst_loss_label": worst_label,
        "session_story": story,
    }
