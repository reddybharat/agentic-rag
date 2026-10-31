import uuid
from types import TracebackType
from typing import Protocol, Self

from langchain_core.language_models import BaseChatModel

from app.domain.models import (
    Capability,
    ChunkHit,
    ChunkIn,
    Document,
    ModelSpec,
    Session,
    TurnUsage,
)


class ChatModelProvider(Protocol):
    def create(self, spec: ModelSpec) -> BaseChatModel: ...


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class SessionRepository(Protocol):
    """Every method is scoped to `owner_id`: another owner's sessions behave as missing."""

    async def add(self, owner_id: str, title: str) -> Session: ...

    async def get(self, owner_id: str, session_id: uuid.UUID) -> Session | None: ...

    async def list_by_owner(self, owner_id: str) -> list[Session]: ...

    async def rename(self, owner_id: str, session_id: uuid.UUID, title: str) -> Session | None: ...

    async def delete(self, owner_id: str, session_id: uuid.UUID) -> bool: ...


class UsageRepository(Protocol):
    async def add(self, usage: TurnUsage) -> None: ...


class DocumentRepository(Protocol):
    """Every method is scoped to `owner_id`: another owner's documents behave as missing."""

    async def add(
        self, owner_id: str, filename: str, sha256: str, embedding_model: str
    ) -> Document: ...

    async def get_by_sha256(self, owner_id: str, sha256: str) -> Document | None: ...

    async def list_by_owner(self, owner_id: str) -> list[Document]: ...

    async def delete(self, owner_id: str, document_id: uuid.UUID) -> bool: ...

    async def has_ready(self, owner_id: str) -> bool: ...

    async def mark_ready(
        self, document_id: uuid.UUID, page_count: int, chunks: list[ChunkIn]
    ) -> None: ...

    async def mark_failed(self, document_id: uuid.UUID, error: str) -> None: ...

    async def search(self, owner_id: str, embedding: list[float], limit: int) -> list[ChunkHit]: ...

    async def has_other_embedding_model(self, embedding_model: str) -> bool: ...


class CapabilityProvider(Protocol):
    def discover(self) -> list[Capability]: ...


class UnitOfWork(Protocol):
    """One transaction; changes are discarded unless `commit()` is called before exit."""

    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def usage(self) -> UsageRepository: ...

    @property
    def documents(self) -> DocumentRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
