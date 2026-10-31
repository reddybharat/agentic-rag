from dataclasses import dataclass
from typing import Self

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.domain.ports import Embedder
from app.infra.db.engine import build_engine
from app.infra.embeddings.ollama import OllamaEmbedder
from app.infra.llm import ollama
from app.infra.llm.model_factory import ModelFactory


@dataclass
class Container:
    """Composition root: the only place concrete adapters are constructed."""

    settings: Settings
    engine: AsyncEngine
    ollama_http: httpx.AsyncClient
    model_factory: ModelFactory
    embedder: Embedder

    @classmethod
    def build(cls, settings: Settings) -> Self:
        return cls(
            settings=settings,
            engine=build_engine(settings.database_url),
            ollama_http=httpx.AsyncClient(
                base_url=settings.ollama_base_url, timeout=settings.readiness_timeout_s
            ),
            model_factory=ModelFactory.from_yaml(
                settings.models_config_path,
                {
                    ollama.PROVIDER_NAME: ollama.OllamaChatProvider(
                        settings.ollama_base_url, settings.llm_timeout_s
                    )
                },
            ),
            embedder=OllamaEmbedder(
                settings.ollama_base_url,
                settings.embedding_model,
                settings.embedding_dim,
                settings.llm_timeout_s,
            ),
        )

    async def aclose(self) -> None:
        await self.ollama_http.aclose()
        await self.engine.dispose()
