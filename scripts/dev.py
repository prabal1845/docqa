"""Run the API locally with an embedded Postgres + pgvector. No Docker needed.

    python scripts/dev.py

Data is kept in .pgdata/ between runs. Gemini settings come from .env.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pgserver
from pgserver.postgres_server import PostgresServer

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".pgdata"


def start_postgres() -> PostgresServer:
    # After an unclean shutdown (terminal closed or PC shut down without Ctrl+C), Postgres
    # runs crash recovery, which can outlast pgserver's 10s startup wait. Postgres keeps
    # starting in the background: the first attempt times out, and later ones fail an
    # assertion while its status is still "starting". Retry until it reports ready.
    for attempt in range(24):
        try:
            return pgserver.get_server(PGDATA)
        except (subprocess.TimeoutExpired, AssertionError):
            # pgserver caches the half-started handle; drop it so the next try starts fresh
            PostgresServer._instances.pop(PGDATA, None)
            if attempt == 0:
                print("Postgres is recovering from an unclean shutdown, waiting...")
            time.sleep(5)
    sys.exit("Postgres didn't start. See .pgdata/log for details.")


def main() -> None:
    server = start_postgres()
    env = dict(
        os.environ,
        DATABASE_URL=server.get_uri().replace("postgresql://", "postgresql+asyncpg://", 1),
        INGEST_MODE="inline",
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True
    )
    print("\n  API docs: http://127.0.0.1:8000/docs  (Ctrl+C to stop)\n")
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--reload"], cwd=ROOT, env=env
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
