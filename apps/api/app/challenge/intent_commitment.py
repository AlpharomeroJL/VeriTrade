import hashlib
import json

from app.models import TradeIntent


def intent_commitment_sha256(intent: TradeIntent) -> str:
    """Deterministic commitment over canonical intent fields (off-chain integrity / demo 'signed intent')."""
    payload = {
        "intent_uuid": intent.intent_uuid,
        "asset": intent.asset,
        "action": intent.action,
        "requested_size": intent.requested_size,
        "approved_size": intent.approved_size,
        "policy_version": intent.policy_version,
        "risk_verdict": intent.risk_verdict,
        "strategy_id": intent.strategy_id,
        "created_at": intent.created_at.isoformat() if intent.created_at else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
