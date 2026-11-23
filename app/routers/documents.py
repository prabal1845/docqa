from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import Document
from app.schemas import DocumentOut
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


async def _get_owned(db: DbSession, user: CurrentUser, document_id: int) -> Document:
    doc = await db.get(Document, document_id)
    # 404 rather than 403 so other users' document IDs aren't discoverable
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.post("", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    request: Request,
    background: BackgroundTasks,
    db: DbSession,
    user: CurrentUser,
) -> Document:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB"
        )
    # Check the magic bytes, not just the client-supplied content type
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are supported")

    doc = Document(owner_id=user.id, filename=(file.filename or "document.pdf")[:255], content=data)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if settings.ingest_mode == "queue":
        await request.app.state.arq.enqueue_job("ingest", doc.id)
    else:
        background.add_task(ingest_document, doc.id)
    return doc


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: DbSession, user: CurrentUser) -> list[Document]:
    result = await db.scalars(
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    )
    return list(result)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, db: DbSession, user: CurrentUser) -> Document:
    return await _get_owned(db, user, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, db: DbSession, user: CurrentUser) -> Response:
    doc = await _get_owned(db, user, document_id)
    await db.delete(doc)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
