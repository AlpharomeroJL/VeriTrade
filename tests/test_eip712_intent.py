"""EIP-712 typed trade intent signing (local dev)."""

from datetime import datetime, timezone

from app.challenge.eip712_intent import (
    build_trade_intent_typed_data,
    eip712_signing_configured,
    sign_trade_intent_typed_data,
    trade_intent_eip712_digest_hex,
    verify_trade_intent_typed_data,
)
from app.config import Settings
from app.models.entities import TradeIntent


def _settings(**kwargs):
    base = dict(
        VERITRADE_API_PORT=34120,
        DATABASE_URL="sqlite:///./t.sqlite",
        VERITRADE_API_BASE_URL="http://localhost:34120",
        VERITRADE_WEB_BASE_URL="http://localhost:34110",
    )
    base.update(kwargs)
    return Settings(**base)


def test_build_trade_intent_typed_data_uses_chain_and_verifying_contract():
    s = _settings(
        ERC8004_DEV_CHAIN_ID="31337",
        VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT="0x0000000000000000000000000000000000000001",
    )
    intent = TradeIntent(
        intent_uuid="00000000-0000-0000-0000-000000000099",
        asset="BTCUSD",
        action="buy",
        requested_size=1.0,
        approved_size=0.5,
        rationale="",
        confidence=0.5,
        strategy_id="baseline_ma",
        policy_version="v1",
        risk_verdict="allow",
        status="approved",
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    td = build_trade_intent_typed_data(s, intent)
    assert td["domain"]["chainId"] == 31337
    assert td["domain"]["verifyingContract"].lower() == "0x0000000000000000000000000000000000000001"
    assert td["message"]["intent_uuid"] == intent.intent_uuid


def test_sign_verify_roundtrip_anvil_default_key():
    s = _settings(
        VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT="0x0000000000000000000000000000000000000001",
        VERITRADE_INTENT_SIGNER_PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    assert eip712_signing_configured(s)
    intent = TradeIntent(
        intent_uuid="u-roundtrip",
        asset="ETHUSD",
        action="sell",
        requested_size=2.0,
        approved_size=2.0,
        rationale="",
        confidence=0.5,
        strategy_id="s",
        policy_version="v1",
        risk_verdict="allow",
        status="approved",
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    sig, addr = sign_trade_intent_typed_data(s, intent, s.veritrade_intent_signer_private_key)
    recovered = verify_trade_intent_typed_data(s, intent, signature_hex=sig)
    assert recovered and recovered.lower() == addr.lower()


def test_eip712_signing_not_configured_without_key():
    s = _settings(VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT="0x0000000000000000000000000000000000000001")
    assert not eip712_signing_configured(s)


def test_trade_intent_eip712_digest_stable():
    s = _settings(
        VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT="0x0000000000000000000000000000000000000001",
    )
    intent = TradeIntent(
        intent_uuid="digest-test",
        asset="BTCUSD",
        action="buy",
        requested_size=1.0,
        approved_size=1.0,
        rationale="",
        confidence=0.5,
        strategy_id="s",
        policy_version="v1",
        risk_verdict="allow",
        status="approved",
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    d1 = trade_intent_eip712_digest_hex(s, intent)
    d2 = trade_intent_eip712_digest_hex(s, intent)
    assert d1 == d2
    assert d1.startswith("0x") and len(d1) == 66
