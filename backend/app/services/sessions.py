import uuid
from collections.abc import Callable

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.errors import NotFoundError
from app.domain.models import DEFAULT_SESSION_TITLE, MAX_TITLE_CHARS, Session
from app.domain.ports import UnitOfWork

log = structlog.get_logger()

TITLE_STRIP_CHARS = " \t\n\"'`.*#"


class SessionService:
    def __init__(
        self,
        uow: Callable[[], UnitOfWork],
        owner_id: str,
        title_model: BaseChatModel,
        title_prompt: str,
    ) -> None:
        self._uow = uow
        self._owner_id = owner_id
        self._title_model = title_model
        self._title_prompt = title_prompt

    async def create(self, title: str | None = None) -> Session:
        async with self._uow() as uow:
            session = await uow.sessions.add(self._owner_id, title or DEFAULT_SESSION_TITLE)
            await uow.commit()
        return session

    async def list_sessions(self) -> list[Session]:
        async with self._uow() as uow:
            return await uow.sessions.list_by_owner(self._owner_id)

    async def get(self, session_id: uuid.UUID) -> Session:
        async with self._uow() as uow:
            session = await uow.sessions.get(self._owner_id, session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        return session

    async def rename(self, session_id: uuid.UUID, title: str) -> Session:
        async with self._uow() as uow:
            session = await uow.sessions.rename(self._owner_id, session_id, title)
            await uow.commit()
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        return session

    async def delete(self, session_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            deleted = await uow.sessions.delete(self._owner_id, session_id)
            await uow.commit()
        if not deleted:
            raise NotFoundError(f"Session {session_id} not found")

    async def auto_title(self, session: Session, first_message: str) -> None:
        """Name a still-untitled session after its first message, using the fast model."""
        if session.title != DEFAULT_SESSION_TITLE:
            return
        # A missing title must not fail the chat turn, so model errors are logged, not raised.
        try:
            reply = await self._title_model.ainvoke(
                [SystemMessage(self._title_prompt), HumanMessage(first_message)]
            )
        except Exception:
            log.warning("auto_title_failed", session_id=str(session.id), exc_info=True)
            return
        title = reply.text.strip(TITLE_STRIP_CHARS)[:MAX_TITLE_CHARS]
        if not title:
            log.warning("auto_title_empty", session_id=str(session.id))
            return
        async with self._uow() as uow:
            await uow.sessions.rename(self._owner_id, session.id, title)
            await uow.commit()
