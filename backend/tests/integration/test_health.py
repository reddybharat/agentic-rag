import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import REQUEST_ID_HEADER, create_app

UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nothing"
UNREACHABLE_OLLAMA_URL = "http://127.0.0.1:1"
FAST_TIMEOUT_S = 0.5


def test_health_ok_and_echoes_request_id() -> None:
    app = create_app(Settings(database_url=UNREACHABLE_DATABASE_URL, log_json=False))
    with TestClient(app) as client:
        response = client.get("/health", headers={REQUEST_ID_HEADER: "abc123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers[REQUEST_ID_HEADER] == "abc123"


def test_ready_is_503_when_dependencies_are_down() -> None:
    settings = Settings(
        database_url=UNREACHABLE_DATABASE_URL,
        ollama_base_url=UNREACHABLE_OLLAMA_URL,
        readiness_timeout_s=FAST_TIMEOUT_S,
        log_json=False,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": False, "ollama": False},
    }


def test_ready_is_200_with_real_dependencies(test_database_url: str) -> None:
    settings = Settings(database_url=test_database_url, log_json=False)
    try:
        httpx.get(f"{settings.ollama_base_url}/api/version", timeout=FAST_TIMEOUT_S)
    except httpx.HTTPError:
        pytest.skip(f"Ollama not reachable at {settings.ollama_base_url}")

    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {"database": True, "ollama": True}
