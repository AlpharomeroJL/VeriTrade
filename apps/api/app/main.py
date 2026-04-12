import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

from app.api.routes import router
from app.config import get_settings
from app.database import init_db

settings = get_settings()

app = FastAPI(title="VeriTrade API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.veritrade_web_base_url, "http://127.0.0.1:" + str(settings.veritrade_web_port)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def on_startup():
    # Under pytest, init_db runs in tests/conftest (before TestClient) — create_all inside
    # Starlette lifespan can stall on Windows + SQLite + TestClient.
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    if os.environ.get("PYTEST") != "1":
        init_db()
    from app.database import get_session_factory
    from app.services import control_service

    db = get_session_factory()()
    try:
        control_service.get_or_create_control(db)
    finally:
        db.close()
    # Defer importing autonomous_service until needed — its import graph can stall TestClient lifespan on Windows.
    if settings.veritrade_autonomous_runner and os.environ.get("PYTEST") != "1":
        from app.services import autonomous_service

        autonomous_service.ensure_runner_started()
