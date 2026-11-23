"""ARQ worker, used when INGEST_MODE=queue. Run with: arq app.worker.WorkerSettings"""

import logging

from arq.connections import RedisSettings

from app.config import get_settings
from app.services.ingestion import ingest_document

logging.basicConfig(level=logging.INFO)


async def ingest(ctx: dict, document_id: int) -> None:
    await ingest_document(document_id)


class WorkerSettings:
    functions = [ingest]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 300
