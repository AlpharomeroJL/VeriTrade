import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.entities import Execution, PerformanceSnapshot, Signal, TradeIntent

os.environ.setdefault("VERITRADE_API_PORT", "34120")
os.environ.setdefault("VERITRADE_WEB_PORT", "34110")
os.environ.setdefault("VERITRADE_API_BASE_URL", "http://localhost:34120")
os.environ.setdefault("VERITRADE_WEB_BASE_URL", "http://localhost:34110")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.config import get_settings

get_settings.cache_clear()

from app.services import risk_engine


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_manual_pause_blocks():
    db = _session()
    sig = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    res = risk_engine.evaluate_signal(
        db,
        sig,
        100.0,
        datetime.utcnow(),
        False,
        manual_pause=True,
        no_trade=False,
    )
    assert res.verdict == "block"
    assert "manual_pause" in res.reasons


def test_stale_data_blocks():
    db = _session()
    sig = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    old = datetime.utcnow() - timedelta(minutes=10)
    res = risk_engine.evaluate_signal(db, sig, 100.0, old, False, False, False)
    assert res.verdict == "block"
    assert "stale_market_data" in res.reasons


def test_volatility_blocks():
    db = _session()
    sig = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    res = risk_engine.evaluate_signal(db, sig, 100.0, datetime.utcnow(), True, False, False)
    assert res.verdict == "block"


def test_duplicate_requires_prior_fill():
    """Unfilled / blocked intents must not suppress the next governed attempt."""
    db = _session()
    sig1 = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig1)
    db.commit()
    db.refresh(sig1)
    intent = TradeIntent(
        intent_uuid="u1",
        asset="BTCUSD",
        action="buy",
        requested_size=100.0,
        approved_size=0.0,
        rationale="blocked",
        confidence=0.9,
        strategy_id="baseline_ma",
        policy_version="v1",
        risk_verdict="block",
        status="escalated_for_review",
        signal_id=sig1.id,
        risk_decision_id=None,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    sig2 = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t2",
        strategy_id="baseline_ma",
    )
    db.add(sig2)
    db.commit()
    db.refresh(sig2)
    assert risk_engine._duplicate_recent(db, sig2, window_minutes=30) is False

    intent2 = TradeIntent(
        intent_uuid="u2",
        asset="BTCUSD",
        action="buy",
        requested_size=100.0,
        approved_size=100.0,
        rationale="ok",
        confidence=0.9,
        strategy_id="baseline_ma",
        policy_version="v1",
        risk_verdict="allow",
        status="executed",
        signal_id=sig1.id,
        risk_decision_id=None,
    )
    db.add(intent2)
    db.commit()
    db.refresh(intent2)
    ex = Execution(
        intent_id=intent2.id,
        venue="paper",
        order_type="market",
        status="filled",
        fill_price=50000.0,
        fill_size=0.002,
        fees=0.05,
        message="ok",
        created_at=datetime.utcnow(),
    )
    db.add(ex)
    db.commit()

    sig3 = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t3",
        strategy_id="baseline_ma",
    )
    db.add(sig3)
    db.commit()
    db.refresh(sig3)
    assert risk_engine._duplicate_recent(db, sig3, window_minutes=30) is True


def test_sell_trims_to_open_position_not_global_cap():
    db = _session()
    db.add(
        PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            equity=10000.0,
            pnl_daily=0.0,
            pnl_total=0.0,
            drawdown=0.0,
            position_notional=520.0,
        )
    )
    sig = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="sell",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    res = risk_engine.evaluate_signal(db, sig, 600.0, datetime.utcnow(), False, False, False)
    assert res.verdict == "allow_with_reduction"
    assert res.approved_size == 520.0
    assert "reduced_to_open_position" in res.reasons


def test_max_position_reduction():
    db = _session()
    db.add(
        PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            equity=10000.0,
            pnl_daily=0.0,
            pnl_total=0.0,
            drawdown=0.0,
            position_notional=400.0,
        )
    )
    sig = Signal(
        asset="BTCUSD",
        timestamp=datetime.utcnow(),
        signal_type="buy",
        confidence=0.9,
        rationale="t",
        strategy_id="baseline_ma",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    res = risk_engine.evaluate_signal(db, sig, 500.0, datetime.utcnow(), False, False, False)
    assert res.verdict == "allow_with_reduction"
    assert res.approved_size == 100.0
