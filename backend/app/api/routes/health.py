import asyncio
from collections.abc import Awaitable

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.deps import ContainerDep
from app.infra.db import engine as db
from app.infra.llm import ollama

log = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check(name: str, probe: Awaitable[None], timeout_s: float) -> bool:
    try:
        await asyncio.wait_for(probe, timeout_s)
    except Exception as exc:
        log.warning("readiness_check_failed", check=name, error=repr(exc))
        return False
    return True


@router.get("/ready")
async def ready(container: ContainerDep) -> JSONResponse:
    timeout_s = container.settings.readiness_timeout_s
    database, ollama_ok = await asyncio.gather(
        _check("database", db.ping(container.engine), timeout_s),
        _check("ollama", ollama.ping(container.ollama_http), timeout_s),
    )
    checks = {"database": database, "ollama": ollama_ok}
    ok = all(checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks},
        status_code=200 if ok else 503,
    )
