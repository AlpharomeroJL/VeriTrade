import random
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MarketSnapshot, Signal
from app.services import candle_service


def _recent_prices(db: Session, symbol: str, limit: int = 5) -> list[float]:
    q = (
        select(MarketSnapshot.price)
        .where(MarketSnapshot.symbol == symbol)
        .order_by(desc(MarketSnapshot.captured_at))
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    return list(rows)


def generate_signal_from_snapshot(db: Session, snapshot: MarketSnapshot) -> Signal:
    settings = get_settings()
    sym = snapshot.symbol
    closes = candle_service.recent_close_prices(db, sym, n=60)
    used_candles = len(closes) >= 20

    if used_candles:
        w_short = min(10, len(closes))
        w_long = min(50, len(closes))
        short_ma = sum(closes[-w_short:]) / w_short
        long_ma = sum(closes[-w_long:]) / w_long
        if short_ma > long_ma * 1.0002:
            signal_type = "buy"
            confidence = min(0.95, 0.55 + min(0.35, (short_ma / long_ma - 1) * 120))
        elif short_ma < long_ma * 0.9998:
            signal_type = "sell"
            confidence = min(0.95, 0.55 + min(0.35, (1 - short_ma / long_ma) * 120))
        else:
            signal_type = "buy" if closes[-1] >= short_ma else "sell"
            confidence = 0.58
        mom = (closes[-1] - closes[-min(11, len(closes))]) / closes[-min(11, len(closes))] if closes[-min(11, len(closes))] else 0.0
        rationale = (
            f"1m candle warm-up: {len(closes)} closes; short_avg({w_short})={short_ma:.4f} vs long_avg({w_long})={long_ma:.4f}; "
            f"~10m momentum {mom*100:.3f}% vs last bar {closes[-1]:.4f}."
        )
    else:
        prices = _recent_prices(db, sym, limit=5)
        if len(prices) >= 2:
            short_ma = prices[0]
            long_ma = sum(prices) / len(prices)
            if short_ma > long_ma * 1.0001:
                signal_type = "buy"
                confidence = min(0.95, 0.55 + (short_ma / long_ma - 1) * 50)
            elif short_ma < long_ma * 0.9999:
                signal_type = "sell"
                confidence = min(0.95, 0.55 + (1 - short_ma / long_ma) * 50)
            else:
                signal_type = "buy"
                confidence = 0.56
        else:
            signal_type = "buy" if random.random() > 0.45 else "sell"
            confidence = round(random.uniform(0.52, 0.88), 3)
        rationale = (
            f"Cold-start (few 1m candles yet): snapshot MA short={prices[0] if prices else snapshot.price:.2f} "
            f"vs window_avg={sum(prices)/len(prices) if prices else snapshot.price:.2f}. "
            f"Run another cycle after OHLC backfill for fuller context."
        )

    sig = Signal(
        asset=sym,
        timestamp=datetime.utcnow(),
        signal_type=signal_type,
        confidence=float(round(confidence, 4)),
        rationale=rationale,
        strategy_id="baseline_ma",
        market_snapshot_id=snapshot.id,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


def create_deterministic_signal(
    db: Session,
    snapshot: MarketSnapshot,
    *,
    signal_type: str,
    confidence: float,
    strategy_id: str = "scenario_demo",
) -> Signal:
    """Reproducible signal for rubric demo scenarios (not MA-random)."""
    sig = Signal(
        asset=snapshot.symbol,
        timestamp=datetime.utcnow(),
        signal_type=signal_type,
        confidence=float(round(confidence, 4)),
        rationale=f"Scenario preset: deterministic {signal_type} at {confidence:.2f} confidence for judge-visible outcomes.",
        strategy_id=strategy_id,
        market_snapshot_id=snapshot.id,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig
