from typing import Annotated

from pydantic import BaseModel, StringConstraints

MAX_MESSAGE_CHARS = 8000


class MessageIn(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_CHARS)
    ]
