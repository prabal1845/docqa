from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import QueryLog
from app.schemas import QueryLogOut, QueryRequest, QueryResponse
from app.services.llm import get_provider
from app.services.rag import answer_question

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest, db: DbSession, user: CurrentUser) -> QueryResponse:
    settings = get_settings()

    # Per-user rolling 24h quota keeps a single account from exhausting the LLM free tier
    since = datetime.now(UTC) - timedelta(days=1)
    used = await db.scalar(
        select(func.count())
        .select_from(QueryLog)
        .where(QueryLog.user_id == user.id, QueryLog.created_at >= since)
    )
    if used >= settings.daily_query_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily limit of {settings.daily_query_limit} questions reached",
        )

    result = await answer_question(
        db,
        get_provider(),
        user.id,
        body.question,
        body.top_k or settings.default_top_k,
        body.document_ids,
    )
    db.add(QueryLog(user_id=user.id, question=body.question, answer=result.answer))
    await db.commit()
    return result


@router.get("/queries", response_model=list[QueryLogOut])
async def query_history(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[QueryLog]:
    result = await db.scalars(
        select(QueryLog)
        .where(QueryLog.user_id == user.id)
        .order_by(QueryLog.created_at.desc(), QueryLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result)
