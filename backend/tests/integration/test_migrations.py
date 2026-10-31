import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.infra.db.engine import build_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _table_names(database_url: str) -> list[str]:
    engine = build_engine(database_url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    finally:
        await engine.dispose()


def test_upgrade_downgrade_upgrade_is_clean(test_database_url: str) -> None:
    config = _alembic_config(test_database_url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert "sessions" not in asyncio.run(_table_names(test_database_url))

    command.upgrade(config, "head")
    assert "sessions" in asyncio.run(_table_names(test_database_url))
