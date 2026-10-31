import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict


class _TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str | None = None


@pytest.fixture
def test_database_url() -> str:
    url = _TestSettings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL not set: needs a disposable Postgres + pgvector database")
    return url
