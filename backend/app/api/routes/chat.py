from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import ChatRequestDep, ChatServiceDep, SessionDep

router = APIRouter(tags=["chat"])


@router.post("/sessions/{session_id}/messages", response_class=EventSourceResponse)
async def send_message(
    session: SessionDep, request: ChatRequestDep, chat: ChatServiceDep
) -> AsyncIterator[ServerSentEvent]:
    """Streams `token`* then `done`, or `error`. The session is resolved before streaming (404)."""
    async for event in chat.stream(session, request.text, request.model_id):
        yield ServerSentEvent(event=event.type, data=event.model_dump(exclude={"type"}))
