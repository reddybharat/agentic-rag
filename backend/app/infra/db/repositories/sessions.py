import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Session
from app.infra.db.orm import SessionRow


class SqlSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, owner_id: str, title: str) -> Session:
        row = SessionRow(owner_id=owner_id, title=title)
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return Session.model_validate(row)

    async def get(self, owner_id: str, session_id: uuid.UUID) -> Session | None:
        row = await self._db.scalar(
            select(SessionRow).where(SessionRow.id == session_id, SessionRow.owner_id == owner_id)
        )
        return None if row is None else Session.model_validate(row)

    async def list_by_owner(self, owner_id: str) -> list[Session]:
        rows = await self._db.scalars(
            select(SessionRow)
            .where(SessionRow.owner_id == owner_id)
            .order_by(SessionRow.updated_at.desc())
        )
        return [Session.model_validate(row) for row in rows]

    async def rename(self, owner_id: str, session_id: uuid.UUID, title: str) -> Session | None:
        row = await self._db.scalar(
            update(SessionRow)
            .where(SessionRow.id == session_id, SessionRow.owner_id == owner_id)
            .values(title=title, updated_at=func.now())
            .returning(SessionRow)
        )
        return None if row is None else Session.model_validate(row)

    async def delete(self, owner_id: str, session_id: uuid.UUID) -> bool:
        deleted = await self._db.scalar(
            delete(SessionRow)
            .where(SessionRow.id == session_id, SessionRow.owner_id == owner_id)
            .returning(SessionRow.id)
        )
        return deleted is not None
