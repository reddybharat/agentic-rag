import time
from collections.abc import AsyncIterator, Callable
from typing import Any, cast

import structlog
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from app.agent.agent_builder import Agent
from app.agent.state import AgentContext
from app.domain.models import (
    ChatEvent,
    DoneEvent,
    ErrorEvent,
    Session,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
    TurnUsage,
)
from app.domain.ports import UnitOfWork
from app.services.sessions import SessionService

log = structlog.get_logger()

MS_PER_S = 1000


class ChatService:
    """Answers one stateless turn: only the system prompt and this message reach the model."""

    def __init__(
        self,
        uow: Callable[[], UnitOfWork],
        agent: Agent,
        model_id: str,
        sessions: SessionService,
    ) -> None:
        self._uow = uow
        self._agent = agent
        self._model_id = model_id
        self._sessions = sessions

    async def stream(self, session: Session, text: str) -> AsyncIterator[ChatEvent]:
        started = time.perf_counter()
        input_tokens = output_tokens = 0
        try:
            # "messages" streams model tokens; "updates" yields each finished node's messages,
            # which is where complete tool calls and tool results appear.
            async for mode, payload in self._agent.astream(
                {"messages": [HumanMessage(text)]},
                stream_mode=["messages", "updates"],
                context=AgentContext(session_id=session.id),
            ):
                if mode == "updates":
                    for event in _tool_events(cast(dict[str, Any], payload)):
                        yield event
                    continue
                chunk, _ = cast(tuple[BaseMessage, dict[str, Any]], payload)
                if not isinstance(chunk, AIMessageChunk):
                    continue
                if chunk.usage_metadata:
                    input_tokens += chunk.usage_metadata["input_tokens"]
                    output_tokens += chunk.usage_metadata["output_tokens"]
                # `.text` holds answer text only; thinking arrives as separate reasoning content.
                if chunk.text:
                    yield TokenEvent(text=chunk.text)
        except Exception:
            log.exception("chat_turn_failed", session_id=str(session.id))
            yield ErrorEvent(code="chat_failed", message="The model failed to answer. Try again.")
            return

        usage = TurnUsage(
            session_id=session.id,
            model_id=self._model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round((time.perf_counter() - started) * MS_PER_S),
        )
        async with self._uow() as uow:
            await uow.usage.add(usage)
            await uow.commit()
        await self._sessions.auto_title(session, text)
        yield DoneEvent(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=usage.latency_ms,
        )


def _tool_events(updates: dict[str, Any]) -> list[ChatEvent]:
    events: list[ChatEvent] = []
    for update in updates.values():
        # Middleware nodes may report `None` instead of a state update.
        if not isinstance(update, dict):
            continue
        for message in update.get("messages", []):
            if isinstance(message, AIMessage):
                events += [
                    ToolStartEvent(id=call["id"] or "", name=call["name"], args=call["args"])
                    for call in message.tool_calls
                ]
            elif isinstance(message, ToolMessage):
                events.append(
                    ToolEndEvent(
                        id=message.tool_call_id,
                        name=message.name or "",
                        ok=message.status != "error",
                    )
                )
    return events
