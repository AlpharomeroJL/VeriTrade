def test_demo_seed_and_run_cycle(client):
    r = client.post("/demo/seed")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True

    r2 = client.post("/demo/run-once")
    assert r2.status_code == 200
    out = r2.json()
    assert out.get("ok") is True

    ov = client.get("/overview").json()
    assert "challenge" in ov
    assert "rubric_metrics" in ov
    assert "challenge_fit" in ov
    assert "safety_strip" in ov
    assert "top_markets" in ov
    assert "autonomous" in ov
    assert "cycle_history" in ov
    assert "risk_full_allow_count" in ov["rubric_metrics"]
    assert "risk_reduced_count" in ov["rubric_metrics"]
    assert ov["rubric_metrics"].get("validation_artifact_count", 0) >= 0
    assert ov["challenge_fit"].get("paper_safe_demo_mode") is True
    assert ov["challenge"].get("agent_id")
    assert ov["challenge"].get("erc8004_draft", {}).get("agent_registration_url")
    assert ov["challenge"].get("kraken_surface", {}).get("routing_mode")
    assert ov["challenge_fit"].get("erc8004_agent_registration_available") is True
    assert ov["latest_signal"] is not None
    assert ov["latest_risk"] is not None
    if not out.get("blocked") and not out.get("escalated") and not out.get("skipped"):
        assert ov["latest_intent"] is not None
        assert ov["latest_execution"] is not None
        assert ov["latest_performance"] is not None

    act = client.get("/activity")
    assert act.status_code == 200
    kinds = {row["kind"] for row in act.json()}
    assert "signal" in kinds
    assert "risk" in kinds
    if not out.get("blocked") and not out.get("escalated") and not out.get("skipped"):
        assert "intent" in kinds
        assert "execution" in kinds


def test_control_pause_blocks_run(client):
    client.post("/demo/seed")
    client.post("/control/pause")
    r = client.post("/demo/run-once")
    assert r.status_code == 200
    assert r.json().get("error") == "system_paused"

    r2 = client.post("/control/step")
    assert r2.status_code == 200
    assert r2.json().get("ok") is True


def test_scenario_safe_allow(client):
    r = client.post("/demo/scenario/safe_allow")
    assert r.status_code == 200
    assert r.json().get("scenario") == "safe_allow"
    ov = client.get("/overview").json()
    assert ov["latest_risk"]["verdict"] == "allow"
    assert ov["market_snapshot"]["volatility_flag"] is False


def test_scenario_volatile_block(client):
    r = client.post("/demo/scenario/volatile_block")
    assert r.status_code == 200
    body = r.json()
    assert body.get("blocked") is True
    ov = client.get("/overview").json()
    assert ov["latest_risk"]["verdict"] == "block"
    assert ov["market_snapshot"]["volatility_flag"] is True


def test_scenario_oversized_reduce(client):
    r = client.post("/demo/scenario/oversized_reduce")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    ov = client.get("/overview").json()
    assert ov["latest_risk"]["verdict"] == "allow_with_reduction"
    assert ov["latest_intent"] is not None
    assert ov["latest_execution"] is not None


def test_scenario_unknown_returns_400(client):
    r = client.post("/demo/scenario/not_a_real_scenario")
    assert r.status_code == 400


def test_autonomous_start_stop(client):
    client.post("/demo/seed")
    r = client.post("/control/autonomous/start?cadence_seconds=15")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body["autonomous"]["enabled"] is True
    assert body["autonomous"]["cadence_seconds"] == 15

    r2 = client.post("/control/autonomous/stop")
    assert r2.status_code == 200
    assert r2.json()["autonomous"]["enabled"] is False


def test_intent_signature_verification_route(client):
    client.post("/demo/seed")
    assert client.post("/demo/scenario/safe_allow").status_code == 200
    ov = client.get("/overview").json()
    assert ov.get("latest_intent")
    iid = ov["latest_intent"]["id"]
    r = client.get(f"/intents/{iid}/signature-verification")
    assert r.status_code == 200
    body = r.json()
    assert body["intent_id"] == iid
    assert body["eip712_digest_hex"].startswith("0x")
    assert len(body["notes"]) >= 0


def test_safe_allow_populates_eip712_when_dev_signer_configured(client, monkeypatch):
    monkeypatch.setenv(
        "VERITRADE_INTENT_SIGNER_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    monkeypatch.setenv(
        "VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT",
        "0x0000000000000000000000000000000000000001",
    )
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        client.post("/demo/seed")
        assert client.post("/demo/scenario/safe_allow").status_code == 200
        ov = client.get("/overview").json()
        li = ov["latest_intent"]
        assert li is not None
        assert li.get("eip712_signature")
        assert li.get("eip712_signer")
        assert li.get("eip712_chain_id") == 31337
        assert ov["challenge"]["erc8004_draft"]["intent_eip712_mode"] == "local_dev_typed_signing_enabled"
    finally:
        monkeypatch.delenv("VERITRADE_INTENT_SIGNER_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT", raising=False)
        get_settings.cache_clear()
