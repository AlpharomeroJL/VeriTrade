import random
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MarketSnapshot


def ingest_for_settings(db: Session) -> MarketSnapshot:
    """Respect MARKET_DATA_MODE — scenarios still call ingest_mock_snapshot directly."""
    settings = get_settings()
    mode = (settings.market_data_mode or "demo").lower()
    if mode == "kraken_public":
        return ingest_kraken_top_snapshots(db)
    if mode == "kraken_cli":
        return ingest_kraken_top_snapshots(db, fetch_mode="cli")
    return ingest_mock_snapshot(db)


def ingest_kraken_top_snapshots(db: Session, *, fetch_mode: str = "https") -> MarketSnapshot:
    """Fetch BTC/USD, ETH/USD, SOL/USD from Kraken public ticker; return latest row for DEFAULT_SYMBOL."""
    from app.adapters.kraken_public_market import (
        TOP_UI_SYMBOLS,
        fetch_ticker_for_ui_symbol,
        fetch_ticker_for_ui_symbol_cli,
    )

    settings = get_settings()
    primary = settings.default_symbol.upper()
    if primary not in TOP_UI_SYMBOLS:
        primary = "BTCUSD"

    last_primary: MarketSnapshot | None = None
    first_ok: MarketSnapshot | None = None
    for ui in TOP_UI_SYMBOLS:
        try:
            row = (
                fetch_ticker_for_ui_symbol_cli(ui)
                if fetch_mode == "cli"
                else fetch_ticker_for_ui_symbol(ui)
            )
            src = row.fetch_via
            vol = False
            if row.bid is not None and row.ask is not None and row.price > 0:
                mid = (row.bid + row.ask) / 2.0
                if mid > 0:
                    vol = (row.ask - row.bid) / mid > 0.012
            snap = MarketSnapshot(
                symbol=ui,
                price=row.price,
                bid=row.bid,
                ask=row.ask,
                volatility_flag=vol,
                source=src,
                captured_at=datetime.utcnow(),
            )
            db.add(snap)
            db.commit()
            db.refresh(snap)
            if first_ok is None:
                first_ok = snap
            if ui == primary:
                last_primary = snap
        except Exception:
            continue

    if last_primary is not None:
        return last_primary
    if first_ok is not None:
        return first_ok

    # Offline / misconfigured CLI — fall back but label exactly why.
    fallback_source = "mock_fallback_cli_unavailable" if fetch_mode == "cli" else "mock_fallback"
    return ingest_mock_snapshot(db, symbol=primary, volatility_flag=False, source_override=fallback_source)


def ingest_mock_snapshot(
    db: Session,
    symbol: str | None = None,
    *,
    volatility_flag: bool | None = None,
    source_override: str | None = None,
    captured_at: datetime | None = None,
) -> MarketSnapshot:
    settings = get_settings()
    sym = symbol or settings.default_symbol
    base = 42000.0 + random.uniform(-200, 200)
    vol = random.random() < 0.08 if volatility_flag is None else bool(volatility_flag)
    cap = captured_at or datetime.utcnow()
    snap = MarketSnapshot(
        symbol=sym,
        price=round(base, 2),
        bid=round(base - 5, 2),
        ask=round(base + 5, 2),
        volatility_flag=vol,
        source=source_override or "mock",
        captured_at=cap,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def get_latest_snapshot(db: Session, symbol: str | None = None) -> MarketSnapshot | None:
    settings = get_settings()
    sym = symbol or settings.default_symbol
    q = select(MarketSnapshot).where(MarketSnapshot.symbol == sym).order_by(desc(MarketSnapshot.captured_at)).limit(1)
    return db.execute(q).scalar_one_or_none()


def snapshot_is_stale(snap: MarketSnapshot, max_age_seconds: int = 120) -> bool:
    cap = snap.captured_at
    if cap.tzinfo is not None:
        cap = cap.replace(tzinfo=None)
    age = datetime.utcnow() - cap
    return age > timedelta(seconds=max_age_seconds)
