import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text

from app.infra.db.engine import build_engine

OLLAMA_PROBE_TIMEOUT_S = 0.5
BACKEND_DIR = Path(__file__).resolve().parents[1]


class _TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str | None = None
    ollama_base_url: str = "http://localhost:11434"


@pytest.fixture
def test_database_url() -> str:
    url = _TestSettings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL not set: needs a disposable Postgres + pgvector database")
    return url


@pytest.fixture
def alembic_config(test_database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", test_database_url)
    return config


async def _execute(database_url: str, sql: str) -> list[tuple[object, ...]]:
    engine = build_engine(database_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(sql))
            return [tuple(row) for row in result] if result.returns_rows else []
    finally:
        await engine.dispose()


@pytest.fixture
def migrated_database_url(test_database_url: str, alembic_config: Config) -> str:
    """The test database at the latest schema, with all app data removed."""
    command.upgrade(alembic_config, "head")
    asyncio.run(_execute(test_database_url, "TRUNCATE sessions, documents CASCADE"))
    return test_database_url


@pytest.fixture
def run_sql(migrated_database_url: str) -> Callable[[str], list[tuple[object, ...]]]:
    return lambda sql: asyncio.run(_execute(migrated_database_url, sql))


@pytest.fixture
def ollama_base_url() -> str:
    url = _TestSettings().ollama_base_url
    try:
        httpx.get(f"{url}/api/version", timeout=OLLAMA_PROBE_TIMEOUT_S)
    except httpx.HTTPError:
        pytest.skip(f"Ollama not reachable at {url}")
    return url
