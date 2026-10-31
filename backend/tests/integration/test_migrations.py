import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.infra.db.engine import build_engine

APP_TABLES = {"sessions", "turn_usage"}


async def _table_names(database_url: str) -> set[str]:
    engine = build_engine(database_url)
    try:
        async with engine.connect() as conn:
            return set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await engine.dispose()


def test_upgrade_downgrade_upgrade_is_clean(test_database_url: str, alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    assert not APP_TABLES & asyncio.run(_table_names(test_database_url))

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_table_names(test_database_url)) >= APP_TABLES
