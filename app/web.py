"""Production entrypoint: the API under /api and the built React app everywhere else.

    uvicorn app.web:app

Serving both from one process means one deploy and no CORS. Keeping the API under /api
means page URLs like /documents never collide with API routes of the same name.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.main import app as api

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """Serve built frontend files, falling back to index.html so that React Router
    handles client-side routes like /chat on a full page load."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Mounted apps don't get lifespan events, so run the API's startup/shutdown from here
    async with api.router.lifespan_context(api):
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)
app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
