from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_SessionLocal = None


def reset_engine() -> None:
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(url, connect_args=connect_args)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _sqlite_patch_legacy_schema(engine) -> None:
    """create_all does not ALTER existing SQLite tables — add columns from older dev DBs."""
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    from sqlalchemy import text

    def colset(conn, table: str) -> set[str]:
        try:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        except Exception:
            return set()
        return {r[1] for r in rows}

    patches: list[tuple[str, str, str]] = [
        ("trade_intents", "lane_id", "VARCHAR(32)"),
        ("trade_intents", "lane_label", "VARCHAR(64)"),
        ("trade_intents", "market_type", "VARCHAR(16)"),
        ("trade_intents", "strategy_family", "VARCHAR(64)"),
        ("trade_intents", "capital_bucket", "FLOAT"),
        ("executions", "lane_id", "VARCHAR(32)"),
        ("executions", "market_type", "VARCHAR(16)"),
        ("executions", "strategy_family", "VARCHAR(64)"),
        ("lane_performance_snapshots", "skip_count", "INTEGER DEFAULT 0"),
        ("trade_intents", "eip712_signature", "TEXT"),
        ("trade_intents", "eip712_signer", "VARCHAR(64)"),
        ("trade_intents", "eip712_chain_id", "INTEGER"),
    ]
    with engine.begin() as conn:
        seen: dict[str, set[str]] = {}
        for table, col, typ in patches:
            if table not in seen:
                seen[table] = colset(conn, table)
            if not seen[table] or col in seen[table]:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
            seen[table].add(col)


def init_db() -> None:
    from app.models import entities  # noqa: F401
    from app.models.base import Base

    eng = get_engine()
    Base.metadata.create_all(bind=eng)
    _sqlite_patch_legacy_schema(eng)
