from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docqa"

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg(cls, url: str) -> str:
        """Accept the plain postgres:// URLs that hosts like Neon and Render hand out."""
        parts = urlsplit(url)
        if parts.scheme in ("postgres", "postgresql"):
            parts = parts._replace(scheme="postgresql+asyncpg")
        if parts.scheme != "postgresql+asyncpg":
            return url
        query = []
        for key, value in parse_qsl(parts.query):
            if key == "sslmode":
                query.append(("ssl", value))  # asyncpg's name for the same option
            elif key != "channel_binding":  # libpq-only option that asyncpg rejects
                query.append((key, value))
        return urlunsplit(parts._replace(query=urlencode(query)))

    redis_url: str = "redis://localhost:6379"

    jwt_secret: str = "dev-secret-change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    llm_provider: Literal["gemini", "fake"] = "gemini"
    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"

    # "inline" runs ingestion as a FastAPI background task; "queue" hands it to the ARQ worker
    ingest_mode: Literal["inline", "queue"] = "inline"
    max_upload_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 150
    default_top_k: int = 5
    daily_query_limit: int = 50

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
