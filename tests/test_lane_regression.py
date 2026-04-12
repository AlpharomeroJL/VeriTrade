"""Lane-aware API and overview — regression without broad scope expansion."""


def test_overview_includes_lane_trust_and_cycle_history_shape(client):
    client.post("/demo/seed")
    client.post("/demo/run-once")
    ov = client.get("/overview").json()
    assert "lane_trust" in ov
    lt = ov["lane_trust"]
    assert isinstance(lt, list)
    ids = {row["lane_id"] for row in lt}
    assert "spot_momentum" in ids
    assert "futures_tactical" in ids
    for row in lt:
        assert "trust_score_0_100" in row
        assert "posture_label" in row
        assert "allow_count" in row
        assert "reduce_count" in row
        assert "block_count" in row
        assert "review_count" in row
        assert "stand_aside_count" in row
        assert isinstance(row["stand_aside_count"], int)
        assert "artifact_count" in row
        assert isinstance(row["artifact_count"], int)
    hist = ov["cycle_history"]
    assert isinstance(hist, list)
    # Keys optional for older rows; structure tolerates empty history in fresh DB
    for item in hist:
        assert "timestamp" in item
        assert "outcome" in item


def test_lane_run_once_returns_ok(client):
    client.post("/demo/seed")
    r = client.post("/lanes/spot_momentum/run-once")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("lane_id") == "spot_momentum"


def test_pipeline_cycle_includes_lane_labels_for_autonomous_history(client):
    """Core pipeline attaches lane_label so autonomous history can annotate (thread off in tests)."""
    client.post("/demo/seed")
    r = client.post("/demo/run-once")
    assert r.status_code == 200
    assert r.json().get("lane_label") == "Core demo pipeline"
