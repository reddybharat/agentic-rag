import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Tier(StrEnum):
    FAST = "fast"
    SMART = "smart"


class ModelSpec(BaseModel):
    """One entry of the chat model catalog (`config/models.yaml`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    provider: str
    model_name: str
    tier: Tier
    supports_tools: bool
    options: dict[str, str | int | float | bool] = {}


DEFAULT_SESSION_TITLE = "New chat"
MAX_TITLE_CHARS = 200


class Session(BaseModel):
    """A chat; each turn is answered on its own (no history) from the owner's document library."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    owner_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class TurnUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: uuid.UUID
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class DocumentStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Document(BaseModel):
    """A PDF in the owner's library, searched by all their sessions once `ready`."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    owner_id: str
    filename: str
    sha256: str
    page_count: int | None
    embedding_model: str
    status: DocumentStatus
    error: str | None
    created_at: datetime


class ChunkIn(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    ordinal: int
    content: str
    embedding: list[float]


class ChunkHit(BaseModel):
    """A search result plus the chunks around it in the same document."""

    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    filename: str
    page: int
    content: str
    context_before: str
    context_after: str


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class ToolStartEvent(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    id: str
    name: str
    args: dict[str, object]


class ToolEndEvent(BaseModel):
    type: Literal["tool_end"] = "tool_end"
    id: str
    name: str
    ok: bool


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    input_tokens: int
    output_tokens: int
    latency_ms: int


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


type ChatEvent = TokenEvent | ToolStartEvent | ToolEndEvent | DoneEvent | ErrorEvent
