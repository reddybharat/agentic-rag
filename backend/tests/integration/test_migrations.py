import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.infra.db.engine import build_engine

APP_TABLES = {"sessions", "turn_usage", "documents", "chunks"}


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


def test_0004_moves_documents_to_the_owner_and_merges_duplicates(
    test_database_url: str, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "0003")
    asyncio.run(_run(test_database_url, "TRUNCATE sessions, documents CASCADE"))
    asyncio.run(
        _run(
            test_database_url,
            "INSERT INTO sessions (id, owner_id, title) VALUES "
            "('00000000-0000-0000-0000-000000000001', 'alice', 'a1'), "
            "('00000000-0000-0000-0000-000000000002', 'alice', 'a2'), "
            "('00000000-0000-0000-0000-000000000003', 'bob', 'b1')",
        )
    )
    asyncio.run(
        _run(
            test_database_url,
            "INSERT INTO documents (id, session_id, filename, sha256, embedding_model, status) "
            "SELECT gen_random_uuid(), s.id, 'f.pdf', 'same-hash', 'm', 'ready' FROM sessions s",
        )
    )

    command.upgrade(alembic_config, "0004")

    owners = asyncio.run(_run(test_database_url, "SELECT owner_id FROM documents ORDER BY 1"))
    assert owners == [("alice",), ("bob",)]
    command.downgrade(alembic_config, "base")


async def _run(database_url: str, sql: str) -> list[tuple[object, ...]]:
    engine = build_engine(database_url)
    try:
        async with engine.begin() as conn:
            result = await conn.exec_driver_sql(sql)
            return [tuple(row) for row in result] if result.returns_rows else []
    finally:
        await engine.dispose()
