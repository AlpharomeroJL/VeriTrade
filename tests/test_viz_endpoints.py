"""Visualization endpoints for chart + paper session summary."""


def test_market_chart_pack(client):
    client.post("/demo/seed")
    r = client.get("/viz/market-chart?symbol=BTCUSD&limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSD"
    assert body.get("interval") == "1m"
    assert "candles" in body
    assert "points" in body
    assert "markers" in body
    assert isinstance(body["candles"], list)
    assert isinstance(body["points"], list)
    assert "context" in body


def test_market_chart_interval_5m(client):
    client.post("/demo/seed")
    r = client.get("/viz/market-chart?symbol=BTCUSD&limit=120&interval=5m")
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "5m"
    assert isinstance(body["candles"], list)


def test_market_chart_invalid_interval(client):
    client.post("/demo/seed")
    r = client.get("/viz/market-chart?symbol=BTCUSD&interval=2w")
    assert r.status_code == 422


def test_paper_session_summary(client):
    client.post("/demo/seed")
    r = client.get("/viz/paper-session")
    assert r.status_code == 200
    b = r.json()
    for k in ("filled_trades", "blocked", "skipped", "reduced", "review", "allow_full", "session_story"):
        assert k in b
