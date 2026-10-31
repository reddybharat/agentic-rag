import uuid
from collections.abc import Callable

from app.core.errors import NotFoundError
from app.domain.models import DEFAULT_SESSION_TITLE, SESSION_TITLE_CHARS, Session
from app.domain.ports import UnitOfWork

TITLE_ELLIPSIS = "…"


class SessionService:
    def __init__(self, uow: Callable[[], UnitOfWork], owner_id: str) -> None:
        self._uow = uow
        self._owner_id = owner_id

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

    async def title_from_message(self, session: Session, first_message: str) -> None:
        """Name a still-untitled session after its first message, cut to a sidebar-sized title."""
        if session.title != DEFAULT_SESSION_TITLE:
            return
        title = " ".join(first_message.split())
        if len(title) > SESSION_TITLE_CHARS:
            title = title[: SESSION_TITLE_CHARS - len(TITLE_ELLIPSIS)].rstrip() + TITLE_ELLIPSIS
        if not title:
            return
        async with self._uow() as uow:
            await uow.sessions.rename(self._owner_id, session.id, title)
            await uow.commit()
