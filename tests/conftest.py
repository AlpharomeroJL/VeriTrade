import importlib
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./pytest_vt.sqlite")
    monkeypatch.setenv("VERITRADE_API_PORT", "34120")
    monkeypatch.setenv("VERITRADE_WEB_PORT", "34110")
    monkeypatch.setenv("VERITRADE_API_BASE_URL", "http://localhost:34120")
    monkeypatch.setenv("VERITRADE_WEB_BASE_URL", "http://localhost:34110")
    monkeypatch.setenv("MARKET_DATA_MODE", "demo")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PYTEST", "1")
    # Prevent background autonomous loop — competes with TestClient for SQLite and can stall pytest.
    monkeypatch.setenv("VERITRADE_AUTONOMOUS_RUNNER", "0")

    from app.config import get_settings

    get_settings.cache_clear()

    import app.database as dbmod

    dbmod.reset_engine()
    # init_db here (not only in app lifespan): create_all under Starlette TestClient startup can hang on Windows+SQLite.
    dbmod.init_db()

    import app.main as mainmod

    importlib.reload(mainmod)

    with TestClient(mainmod.app) as c:
        yield c

    get_settings.cache_clear()
    dbmod.reset_engine()
