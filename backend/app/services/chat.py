import time
from collections.abc import AsyncIterator, Callable, Mapping
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
from app.core.errors import UnknownModelError
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
TOOL_LIMIT_PREFIX = "Tool call limit exceeded"


class ChatService:
    """Answers one stateless turn: only the system prompt and this message reach the model."""

    def __init__(
        self,
        uow: Callable[[], UnitOfWork],
        agents: Mapping[str, Agent],
        sessions: SessionService,
    ) -> None:
        self._uow = uow
        self._agents = agents
        self._default_model_id = next(iter(agents))
        self._sessions = sessions

    def resolve_model_id(self, model_id: str | None) -> str:
        """The requested model, or the default (the catalog's first); unknown ids are rejected."""
        if model_id is None:
            return self._default_model_id
        if model_id not in self._agents:
            raise UnknownModelError(f"Unknown model {model_id!r}")
        return model_id

    async def stream(self, session: Session, text: str, model_id: str) -> AsyncIterator[ChatEvent]:
        started = time.perf_counter()
        turn_log = log.bind(session_id=str(session.id), owner_id=session.owner_id)
        turn_log.info("turn_started", model_id=model_id, message_chars=len(text))
        tool_started: dict[str, float] = {}
        input_tokens = output_tokens = 0
        try:
            # "messages" streams model tokens; "updates" yields each finished node's messages,
            # which is where complete tool calls and tool results appear.
            async for mode, payload in self._agents[model_id].astream(
                {"messages": [HumanMessage(text)]},
                stream_mode=["messages", "updates"],
                context=AgentContext(owner_id=session.owner_id),
            ):
                if mode == "updates":
                    for event in _tool_events(cast(dict[str, Any], payload)):
                        _log_tool_event(turn_log, event, tool_started)
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
            turn_log.exception("turn_failed")
            yield ErrorEvent(code="chat_failed", message="The model failed to answer. Try again.")
            return

        usage = TurnUsage(
            session_id=session.id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round((time.perf_counter() - started) * MS_PER_S),
        )
        async with self._uow() as uow:
            await uow.usage.add(usage)
            await uow.commit()
        await self._sessions.title_from_message(session, text)
        turn_log.info(
            "turn_done",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=usage.latency_ms,
        )
        yield DoneEvent(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=usage.latency_ms,
        )


def _log_tool_event(
    turn_log: structlog.typing.FilteringBoundLogger, event: ChatEvent, started: dict[str, float]
) -> None:
    if isinstance(event, ToolStartEvent):
        started[event.id] = time.perf_counter()
        turn_log.info("tool_start", tool=event.name, tool_call_id=event.id)
    elif isinstance(event, ToolEndEvent):
        begun = started.pop(event.id, None)
        duration_ms = None if begun is None else round((time.perf_counter() - begun) * MS_PER_S)
        emit = turn_log.info if event.ok else turn_log.warning
        emit(
            "tool_end", tool=event.name, tool_call_id=event.id, ok=event.ok, duration_ms=duration_ms
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
                if str(message.content).startswith(TOOL_LIMIT_PREFIX):
                    log.warning("tool_limit_reached", tool=message.name)
                events.append(
                    ToolEndEvent(
                        id=message.tool_call_id,
                        name=message.name or "",
                        ok=message.status != "error",
                    )
                )
    return events
