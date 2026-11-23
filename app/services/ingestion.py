import asyncio
import logging

from sqlalchemy.orm import undefer

from app.config import get_settings
from app.db import SessionLocal
from app.models import Chunk, Document, DocumentStatus
from app.services.chunking import chunk_pages, extract_pages
from app.services.llm import get_provider

logger = logging.getLogger(__name__)


async def ingest_document(document_id: int) -> None:
    """Extract, chunk and embed a PDF. Runs in a background task or the ARQ worker,
    so it owns its DB session and records failures on the document instead of raising."""
    settings = get_settings()
    async with SessionLocal() as db:
        doc = await db.get(Document, document_id, options=[undefer(Document.content)])
        if doc is None or doc.status == DocumentStatus.READY:
            return
        doc.status = DocumentStatus.PROCESSING
        await db.commit()

        try:
            # pypdf is CPU-bound; keep it off the event loop
            pages = await asyncio.to_thread(extract_pages, doc.content or b"")
            pieces = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
            if not pieces:
                raise ValueError("No extractable text found (scanned/image PDFs aren't supported)")

            vectors = await get_provider().embed([p.content for p in pieces])
            db.add_all(
                Chunk(
                    document_id=doc.id,
                    chunk_index=i,
                    page=piece.page,
                    content=piece.content,
                    embedding=vector,
                )
                for i, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
            )
            doc.page_count = len(pages)
            doc.chunk_count = len(pieces)
            doc.status = DocumentStatus.READY
            doc.content = None
            await db.commit()
            logger.info("Ingested document %s: %s chunks", doc.id, len(pieces))
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            await db.rollback()
            doc = await db.get(Document, document_id)
            if doc is not None:
                doc.status = DocumentStatus.FAILED
                doc.error = str(exc)[:500]
                await db.commit()
