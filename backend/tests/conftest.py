import httpx
import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

OLLAMA_PROBE_TIMEOUT_S = 0.5


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
def ollama_base_url() -> str:
    url = _TestSettings().ollama_base_url
    try:
        httpx.get(f"{url}/api/version", timeout=OLLAMA_PROBE_TIMEOUT_S)
    except httpx.HTTPError:
        pytest.skip(f"Ollama not reachable at {url}")
    return url
