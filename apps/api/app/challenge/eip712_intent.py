"""EIP-712 typed trade intents — local/dev signing with eth-account (optional private key)."""

from __future__ import annotations

from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from app.config import Settings
from app.models import TradeIntent


def trade_intent_eip712_digest_bytes(settings: Settings, intent: TradeIntent) -> bytes:
    """EIP-712 v4 digest bytes32: keccak256(0x19 ‖ 0x01 ‖ domainSeparator ‖ hashStruct(message)).

    eth-account does not expose a stable public API for this digest alone; `message_hash` on a signed
    payload is identical for any signer and matches Solidity/OpenZeppelin EIP-712 signing digests.
    """
    sm = encode_typed_data(full_message=build_trade_intent_typed_data(settings, intent))
    mh = Account.create().sign_message(sm).message_hash
    return bytes(mh)


def trade_intent_eip712_digest_hex(settings: Settings, intent: TradeIntent) -> str:
    return "0x" + trade_intent_eip712_digest_bytes(settings, intent).hex()


def trade_intent_message_dict(intent: TradeIntent) -> dict[str, str]:
    return {
        "intent_uuid": str(intent.intent_uuid),
        "asset": str(intent.asset),
        "action": str(intent.action),
        "requested_size": str(intent.requested_size),
        "approved_size": str(intent.approved_size),
        "policy_version": str(intent.policy_version),
        "risk_verdict": str(intent.risk_verdict),
        "strategy_id": str(intent.strategy_id),
        "created_at": intent.created_at.isoformat() if intent.created_at else "",
    }


def build_trade_intent_typed_data(settings: Settings, intent: TradeIntent) -> dict[str, Any]:
    """Full EIP-712 payload suitable for encode_typed_data / wallet signing."""
    vc = (settings.veritrade_intent_eip712_verifying_contract or "").strip() or "0x0000000000000000000000000000000000000000"
    chain_id = int(settings.erc8004_dev_chain_id)
    return {
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
        "primaryType": "TradeIntent",
        "domain": {
            "name": settings.veritrade_intent_eip712_domain_name,
            "version": settings.veritrade_intent_eip712_domain_version,
            "chainId": chain_id,
            "verifyingContract": vc,
        },
        "message": trade_intent_message_dict(intent),
    }


def eip712_signing_configured(settings: Settings) -> bool:
    pk = (settings.veritrade_intent_signer_private_key or "").strip()
    vc = (settings.veritrade_intent_eip712_verifying_contract or "").strip()
    if not pk or not vc:
        return False
    if vc.lower() == "0x0000000000000000000000000000000000000000":
        return False
    return True


def sign_trade_intent_typed_data(settings: Settings, intent: TradeIntent, private_key_hex: str) -> tuple[str, str]:
    """Returns (0x signature hex, signer checksummed address)."""
    full_message = build_trade_intent_typed_data(settings, intent)
    key = private_key_hex.strip()
    if key.startswith("0x"):
        key = key[2:]
    acct = Account.from_key("0x" + key)
    encoded = encode_typed_data(full_message=full_message)
    signed = acct.sign_message(encoded)
    return "0x" + signed.signature.hex(), acct.address


def verify_trade_intent_typed_data(
    settings: Settings,
    intent: TradeIntent,
    *,
    signature_hex: str,
) -> str | None:
    """Recovers signer address from signature, or None on failure."""
    full_message = build_trade_intent_typed_data(settings, intent)
    try:
        encoded = encode_typed_data(full_message=full_message)
        sig = signature_hex if signature_hex.startswith("0x") else "0x" + signature_hex
        return Account.recover_message(encoded, signature=sig)
    except Exception:
        return None
