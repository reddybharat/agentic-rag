from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Self

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agent.agent_builder import build_agent
from app.agent.skill_loader import load_skills
from app.agent.tools import make_retrieve_from_documents
from app.core.config import Settings
from app.domain.ports import Embedder
from app.infra.db.engine import build_engine, build_session_factory
from app.infra.db.unit_of_work import SqlUnitOfWork
from app.infra.embeddings.ollama import OllamaEmbedder
from app.infra.llm import ollama
from app.infra.llm.model_factory import ModelFactory
from app.infra.rag.chunkers import split_words
from app.infra.rag.pdf_loader import load_pdf_pages
from app.services.chat import ChatService
from app.services.documents import DocumentService
from app.services.sessions import SessionService

PROMPTS_DIR = Path(__file__).parent / "agent" / "prompts"


def _prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


@dataclass
class Container:
    """Composition root: the only place concrete adapters are constructed."""

    settings: Settings
    engine: AsyncEngine
    ollama_http: httpx.AsyncClient
    model_factory: ModelFactory
    embedder: Embedder
    sessions: SessionService
    documents: DocumentService
    chat: ChatService

    @classmethod
    def build(cls, settings: Settings) -> Self:
        engine = build_engine(settings.database_url)
        uow = partial(SqlUnitOfWork, build_session_factory(engine))
        model_factory = ModelFactory.from_yaml(
            settings.models_config_path,
            {
                ollama.PROVIDER_NAME: ollama.OllamaChatProvider(
                    settings.ollama_base_url, settings.llm_timeout_s
                )
            },
        )
        sessions = SessionService(uow, settings.default_owner_id)
        embedder = OllamaEmbedder(
            settings.ollama_base_url,
            settings.embedding_model,
            settings.embedding_dim,
            settings.llm_timeout_s,
        )
        documents = DocumentService(
            uow,
            settings.default_owner_id,
            embedder,
            load_pdf_pages,
            split_words,
            settings.max_upload_bytes,
        )
        return cls(
            settings=settings,
            engine=engine,
            ollama_http=httpx.AsyncClient(
                base_url=settings.ollama_base_url, timeout=settings.readiness_timeout_s
            ),
            model_factory=model_factory,
            embedder=embedder,
            sessions=sessions,
            documents=documents,
            chat=ChatService(
                uow,
                build_agent(
                    model_factory.model,
                    _prompt("system"),
                    load_skills(),
                    [make_retrieve_from_documents(documents.search)],
                ),
                model_factory.spec.id,
                sessions,
            ),
        )

    async def aclose(self) -> None:
        await self.ollama_http.aclose()
        await self.engine.dispose()
