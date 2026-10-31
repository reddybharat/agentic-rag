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
    """A document workspace; each chat turn in it is answered on its own (no history)."""

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


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    input_tokens: int
    output_tokens: int
    latency_ms: int


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


type ChatEvent = TokenEvent | DoneEvent | ErrorEvent
