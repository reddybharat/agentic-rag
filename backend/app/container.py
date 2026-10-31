from dataclasses import dataclass
from typing import Self

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.infra.db.engine import build_engine


@dataclass
class Container:
    """Composition root: the only place concrete adapters are constructed."""

    settings: Settings
    engine: AsyncEngine
    ollama_http: httpx.AsyncClient

    @classmethod
    def build(cls, settings: Settings) -> Self:
        return cls(
            settings=settings,
            engine=build_engine(settings.database_url),
            ollama_http=httpx.AsyncClient(
                base_url=settings.ollama_base_url, timeout=settings.readiness_timeout_s
            ),
        )

    async def aclose(self) -> None:
        await self.ollama_http.aclose()
        await self.engine.dispose()
