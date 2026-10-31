import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, health, models, sessions
from app.container import Container
from app.core.config import Settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

REQUEST_ID_HEADER = "X-Request-ID"
MS_PER_S = 1000

log = structlog.get_logger()


def _request_fields(request: Request, status: int, started: float) -> dict[str, object]:
    return {
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * MS_PER_S),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = Container.build(settings)
        app.state.container = container
        try:
            yield
        finally:
            await container.aclose()

    app = FastAPI(title="Agentic RAG", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)

    @app.middleware("http")
    async def bind_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.error("http_request", **_request_fields(request, 500, started))
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        # For SSE the duration is time to the first byte; `turn_done` carries the full turn.
        log.info("http_request", **_request_fields(request, response.status_code, started))
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(sessions.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app
