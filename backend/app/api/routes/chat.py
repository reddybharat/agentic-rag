from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import ChatServiceDep, SessionDep
from app.api.schemas.chat import MessageIn

router = APIRouter(tags=["chat"])


@router.post("/sessions/{session_id}/messages", response_class=EventSourceResponse)
async def send_message(
    session: SessionDep, body: MessageIn, chat: ChatServiceDep
) -> AsyncIterator[ServerSentEvent]:
    """Streams `token`* then `done`, or `error`. The session is resolved before streaming (404)."""
    async for event in chat.stream(session, body.text):
        yield ServerSentEvent(event=event.type, data=event.model_dump(exclude={"type"}))
