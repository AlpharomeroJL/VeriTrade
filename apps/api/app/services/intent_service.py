import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.challenge.eip712_intent import (
    eip712_signing_configured,
    sign_trade_intent_typed_data,
    verify_trade_intent_typed_data,
)
from app.config import get_settings
from app.models import TradeIntent


def _attach_eip712_if_configured(db: Session, row: TradeIntent) -> None:
    s = get_settings()
    if not eip712_signing_configured(s):
        return
    pk = (s.veritrade_intent_signer_private_key or "").strip()
    try:
        sig, _addr = sign_trade_intent_typed_data(s, row, pk)
    except Exception:
        return
    recovered = verify_trade_intent_typed_data(s, row, signature_hex=sig)
    if not recovered:
        return
    row.eip712_signature = sig
    row.eip712_signer = recovered
    row.eip712_chain_id = s.erc8004_dev_chain_id
    db.add(row)
    db.commit()
    db.refresh(row)


def create_intent(
    db: Session,
    *,
    asset: str,
    action: str,
    requested_size: float,
    approved_size: float,
    rationale: str,
    confidence: float,
    strategy_id: str,
    policy_version: str,
    risk_verdict: str,
    signal_id: int | None,
    risk_decision_id: int | None,
    status: str = "approved",
    lane_id: str | None = None,
    lane_label: str | None = None,
    market_type: str | None = None,
    strategy_family: str | None = None,
    capital_bucket: float | None = None,
) -> TradeIntent:
    row = TradeIntent(
        intent_uuid=str(uuid.uuid4()),
        asset=asset,
        action=action,
        requested_size=requested_size,
        approved_size=approved_size,
        rationale=rationale,
        confidence=confidence,
        strategy_id=strategy_id,
        policy_version=policy_version,
        risk_verdict=risk_verdict,
        status=status,
        created_at=datetime.utcnow(),
        signal_id=signal_id,
        risk_decision_id=risk_decision_id,
        lane_id=lane_id,
        lane_label=lane_label,
        market_type=market_type,
        strategy_family=strategy_family,
        capital_bucket=capital_bucket,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _attach_eip712_if_configured(db, row)
    return row
