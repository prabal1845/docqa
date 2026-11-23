from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import DocumentStatus


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt only uses the first 72 bytes, so cap length rather than silently truncate
    password: str = Field(min_length=8, max_length=64)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: DocumentStatus
    error: str | None
    page_count: int | None
    chunk_count: int
    created_at: datetime


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_ids: list[int] | None = Field(
        default=None, description="Restrict the search to these documents; omit to search all"
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    index: int
    document_id: int
    filename: str
    page: int
    snippet: str
    score: float = Field(description="Cosine similarity, 1.0 is identical")
    cited: bool = Field(description="Whether the answer actually referenced this source")


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


class QueryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    created_at: datetime
