"""LLM provider abstraction: Gemini in production, a deterministic fake for tests."""

import math
import re
import zlib
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models import EMBEDDING_DIM

EMBED_BATCH_SIZE = 100


class LLMProvider(Protocol):
    async def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]: ...

    async def generate(self, prompt: str) -> str: ...


def _is_retryable(exc: BaseException) -> bool:
    # Retry rate limits and server errors; a 400 (bad request) will never succeed on retry
    return isinstance(exc, genai_errors.APIError) and (exc.code == 429 or exc.code >= 500)


_retry_policy = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, max=20),
    reraise=True,
)


class GeminiProvider:
    def __init__(self, api_key: str, chat_model: str, embed_model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            vectors.extend(await self._embed_batch(batch, config))
        return vectors

    @_retry_policy
    async def _embed_batch(
        self, batch: list[str], config: types.EmbedContentConfig
    ) -> list[list[float]]:
        response = await self._client.aio.models.embed_content(
            model=self._embed_model, contents=batch, config=config
        )
        return [list(e.values) for e in response.embeddings]

    @_retry_policy
    async def generate(self, prompt: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return (response.text or "").strip()


class FakeProvider:
    """Hashed bag-of-words embeddings: no network, deterministic, and similar text still
    lands close together, so retrieval tests are meaningful."""

    async def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def generate(self, prompt: str) -> str:
        return "Based on the provided documents [1], here is a summary of the relevant passage."

    @staticmethod
    def _vector(text: str) -> list[float]:
        vec = [0.0] * EMBEDDING_DIM
        vec[0] = 0.01  # avoid a zero vector, whose cosine distance is undefined
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            if len(token) > 2:
                vec[zlib.crc32(token.encode()) % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec]


@lru_cache
def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "fake":
        return FakeProvider()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (or use LLM_PROVIDER=fake)")
    return GeminiProvider(
        settings.gemini_api_key, settings.gemini_chat_model, settings.gemini_embed_model
    )
