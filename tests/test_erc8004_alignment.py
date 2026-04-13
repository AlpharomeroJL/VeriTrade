"""ERC-8004 draft alignment — registration file, hashes, API surfaces."""

from app.challenge.erc8004_validation import (
    validation_request_hash_from_canonical_payload,
)
from app.challenge.registration import build_agent_registration
from app.config import get_settings


def test_agent_registration_matches_eip_type():
    reg = build_agent_registration(get_settings())
    assert reg["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    assert reg["name"]
    assert isinstance(reg["services"], list)
    assert reg["services"]
    assert reg["registrations"] == []


def test_validation_request_hash_keccak_hex():
    h = validation_request_hash_from_canonical_payload({"z": 1, "a": 2})
    assert h.startswith("0x")
    assert len(h) == 66


def test_challenge_agent_registration_route(client):
    r = client.get("/challenge/agent-registration")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"


def test_challenge_erc8004_shapes_route(client):
    r = client.get("/challenge/erc8004-shapes")
    assert r.status_code == 200
    body = r.json()
    assert "validation_request_example" in body
    assert "_comment" in body["validation_request_example"]


def test_challenge_agent_registration_verify_route(client):
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        r = client.get("/challenge/agent-registration/verify")
        assert r.status_code == 200
        body = r.json()
        assert "verification_label" in body
        assert "urls" in body
        assert "fetch" in body
        assert "transport_observation" in body
        assert "registrations_agent_uri" in body
    finally:
        get_settings.cache_clear()


def test_challenge_erc8004_onchain_read_skipped_without_rpc(client):
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        r = client.get("/challenge/erc8004/onchain-read")
        assert r.status_code == 200
        body = r.json()
        assert body.get("rpc_configured") is False
        assert "skipped_reason" in body
    finally:
        get_settings.cache_clear()


def test_agent_registration_includes_agent_wallet_when_placeholder_set(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("VERITRADE_AGENT_WALLET_PLACEHOLDER", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
    get_settings.cache_clear()
    try:
        r = client.get("/challenge/agent-registration")
        assert r.status_code == 200
        assert r.json()["agentWallet"] == "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    finally:
        monkeypatch.delenv("VERITRADE_AGENT_WALLET_PLACEHOLDER", raising=False)
        get_settings.cache_clear()


def test_agent_registration_env_registry_binding(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ERC8004_IDENTITY_REGISTRY_ADDRESS", "0x1111111111111111111111111111111111111111")
    monkeypatch.setenv("ERC8004_ONCHAIN_AGENT_ID", "42")
    get_settings.cache_clear()
    try:
        r = client.get("/challenge/agent-registration")
        assert r.status_code == 200
        reg = r.json()["registrations"]
        assert len(reg) == 1
        assert reg[0]["agentRegistry"].lower() == "0x1111111111111111111111111111111111111111"
        assert reg[0]["agentId"] == "42"
        assert "agentURI" in reg[0]
    finally:
        monkeypatch.delenv("ERC8004_IDENTITY_REGISTRY_ADDRESS", raising=False)
        monkeypatch.delenv("ERC8004_ONCHAIN_AGENT_ID", raising=False)
        get_settings.cache_clear()


def test_identity_wallet_eip712_typed_data_shape():
    from app.challenge.identity_wallet_eip712 import build_set_agent_wallet_typed_data

    td = build_set_agent_wallet_typed_data(
        chain_id=31337,
        verifying_contract="0x0000000000000000000000000000000000000001",
        agent_id=1,
        new_wallet="0x0000000000000000000000000000000000000002",
        nonce=0,
    )
    assert td["primaryType"] == "SetAgentWallet"
    assert td["domain"]["name"] == "VeriTradeLocalIdentityRegistry"
    assert td["message"]["agentId"] == 1


def test_artifact_validation_emit_disabled_by_default():
    from pathlib import Path

    from app.challenge.erc8004_artifact_validation_bridge import maybe_emit_validation_request_for_artifact
    from app.config import get_settings

    s = get_settings()
    assert (
        maybe_emit_validation_request_for_artifact(
            s,
            artifact_type="execution",
            artifact_id=1,
            related_id="x",
            payload={},
            artifact_json_path=Path("/tmp/nope.json"),
        )
        is None
    )


def test_eip1271_generic_matches_adapter_signature():
    import inspect
    from app.challenge import eip1271_intent

    src = inspect.getsource(eip1271_intent.verify_eip1271_is_valid_signature)
    assert "verify_trade_intent_eip1271_adapter" in src
