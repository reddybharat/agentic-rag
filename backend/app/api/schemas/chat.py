from typing import Annotated

from pydantic import BaseModel, StringConstraints

MAX_MESSAGE_CHARS = 8000


class MessageIn(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_CHARS)
    ]
    model_id: str | None = None


class ChatRequest(BaseModel):
    """A validated message with the model that will answer it."""

    text: str
    model_id: str
