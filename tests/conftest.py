"""Tests run against real Postgres + pgvector.

CI sets TEST_DATABASE_URL to a service container; locally an embedded server (pgserver)
is started in a temp directory, so no Docker is needed.
"""

import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    import pgserver

    server = pgserver.get_server(tempfile.mkdtemp(prefix="docqa-pg-"), cleanup_mode="stop")
    return server.get_uri().replace("postgresql://", "postgresql+asyncpg://", 1)


# Must happen before any app module is imported, since settings and the engine load at import
os.environ.update(
    DATABASE_URL=_database_url(),
    LLM_PROVIDER="fake",
    INGEST_MODE="inline",
    JWT_SECRET="test-secret-that-is-at-least-32-bytes-long",
)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")
    # One client for the session keeps a single event loop for the async engine's pool
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    yield

    async def truncate():
        async with engine.begin() as conn:
            await conn.execute(
                text("TRUNCATE users, documents, chunks, query_logs RESTART IDENTITY CASCADE")
            )

    client.portal.call(truncate)
