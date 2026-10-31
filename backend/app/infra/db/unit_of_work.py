from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.repositories.sessions import SqlSessionRepository
from app.infra.db.repositories.usage import SqlUsageRepository


class SqlUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._db = session_factory()
        self.sessions = SqlSessionRepository(self._db)
        self.usage = SqlUsageRepository(self._db)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Closing without a commit rolls the transaction back.
        await self._db.close()

    async def commit(self) -> None:
        await self._db.commit()
