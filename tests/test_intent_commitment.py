from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.challenge.intent_commitment import intent_commitment_sha256
from app.models.base import Base
from app.models.entities import TradeIntent


def test_intent_commitment_is_stable():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    row = TradeIntent(
        intent_uuid="u1",
        asset="BTCUSD",
        action="buy",
        requested_size=100.0,
        approved_size=100.0,
        rationale="t",
        confidence=0.8,
        strategy_id="s",
        policy_version="v1",
        risk_verdict="allow",
        status="approved",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    a = intent_commitment_sha256(row)
    b = intent_commitment_sha256(row)
    assert len(a) == 64
    assert a == b
