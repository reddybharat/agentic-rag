import time
from collections.abc import AsyncIterator, Callable

import structlog
from langchain_core.messages import AIMessageChunk, HumanMessage

from app.agent.agent_builder import Agent
from app.domain.models import ChatEvent, DoneEvent, ErrorEvent, Session, TokenEvent, TurnUsage
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
            async for chunk, _ in self._agent.astream(
                {"messages": [HumanMessage(text)]}, stream_mode="messages"
            ):
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
