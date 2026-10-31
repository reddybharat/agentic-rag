from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import REQUEST_ID_HEADER, create_app

UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nothing"
UNREACHABLE_OLLAMA_URL = "http://127.0.0.1:1"
FAST_TIMEOUT_S = 0.5
type RunSql = Callable[[str], list[tuple[object, ...]]]


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
        "checks": {"database": False, "ollama": False, "embeddings": False},
    }


def test_ready_is_200_with_real_dependencies(
    migrated_database_url: str, ollama_base_url: str
) -> None:
    settings = Settings(
        database_url=migrated_database_url, ollama_base_url=ollama_base_url, log_json=False
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {"database": True, "ollama": True, "embeddings": True}


def test_ready_fails_when_documents_use_another_embedding_model(
    migrated_database_url: str, run_sql: RunSql
) -> None:
    run_sql(
        "INSERT INTO documents (id, owner_id, filename, sha256, embedding_model, status) "
        "VALUES (gen_random_uuid(), 'local', 'a.pdf', 'x', 'other-embedder', 'ready')"
    )
    with TestClient(create_app(Settings(database_url=migrated_database_url))) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["embeddings"] is False
