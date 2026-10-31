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
    google_api_key: str | None = None
    groq_api_key: str | None = None


# Read once at import, before the autouse fixture below overrides the variables for every test.
REAL_GOOGLE_API_KEY = _TestSettings().google_api_key
REAL_GROQ_API_KEY = _TestSettings().groq_api_key
FAKE_GROQ_API_KEY = "not-a-real-key"  # building a Groq client makes no network call


@pytest.fixture(autouse=True)
def _no_real_chat_keys_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gemini is skipped and Groq gets a fake key, so the app starts with a Groq default model
    and tests never spend quota or leave the machine unless they ask for a real key fixture."""
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", FAKE_GROQ_API_KEY)


@pytest.fixture
def google_api_key() -> str:
    if not REAL_GOOGLE_API_KEY:
        pytest.skip("GOOGLE_API_KEY not set")
    return REAL_GOOGLE_API_KEY


@pytest.fixture
def groq_api_key() -> str:
    if not REAL_GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not set")
    return REAL_GROQ_API_KEY


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
