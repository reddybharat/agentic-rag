from typing import Protocol

from langchain_core.language_models import BaseChatModel

from app.domain.models import ModelSpec


class ChatModelProvider(Protocol):
    def create(self, spec: ModelSpec) -> BaseChatModel: ...


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...
