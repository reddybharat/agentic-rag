from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import TurnUsage
from app.infra.db.orm import TurnUsageRow


class SqlUsageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, usage: TurnUsage) -> None:
        self._db.add(TurnUsageRow(**usage.model_dump()))
