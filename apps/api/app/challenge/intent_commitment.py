import hashlib
import json

from app.models import TradeIntent


def trade_intent_eip712_outline(intent: TradeIntent) -> dict:
    """Typed-data *outline* for judges — not a signed EIP-712 payload (no wallet, no chainId binding yet)."""
    msg = {
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
    return {
        "primaryType": "TradeIntent",
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TradeIntent": [
                {"name": "intent_uuid", "type": "string"},
                {"name": "asset", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "requested_size", "type": "string"},
                {"name": "approved_size", "type": "string"},
                {"name": "policy_version", "type": "string"},
                {"name": "risk_verdict", "type": "string"},
                {"name": "strategy_id", "type": "string"},
                {"name": "created_at", "type": "string"},
            ],
        },
        "domain": {
            "name": "VeriTrade",
            "version": "1",
            "chainId": 0,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "message": {
            "intent_uuid": str(msg["intent_uuid"]),
            "asset": str(msg["asset"]),
            "action": str(msg["action"]),
            "requested_size": str(msg["requested_size"]),
            "approved_size": str(msg["approved_size"]),
            "policy_version": str(msg["policy_version"]),
            "risk_verdict": str(msg["risk_verdict"]),
            "strategy_id": str(msg["strategy_id"]),
            "created_at": str(msg["created_at"] or ""),
        },
        "_note": "VeriTrade currently commits via SHA256(canonical JSON) — see intent_commitment_sha256. "
        "Wiring to typedDataSign / registry attestation would replace chainId and verifyingContract.",
    }


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
