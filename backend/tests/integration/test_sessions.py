import uuid

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.models import DEFAULT_SESSION_TITLE
from app.main import create_app


def _client(database_url: str, owner_id: str = "local") -> TestClient:
    return TestClient(
        create_app(Settings(database_url=database_url, default_owner_id=owner_id, log_json=False))
    )


def test_session_crud(migrated_database_url: str) -> None:
    with _client(migrated_database_url) as client:
        untitled = client.post("/sessions", json={})
        titled = client.post("/sessions", json={"title": "  Trip plans  "})
        assert untitled.status_code == titled.status_code == 201
        assert untitled.json()["title"] == DEFAULT_SESSION_TITLE
        assert titled.json()["title"] == "Trip plans"
        session_id = titled.json()["id"]

        listed = client.get("/sessions").json()
        assert [s["id"] for s in listed] == [session_id, untitled.json()["id"]]

        renamed = client.patch(f"/sessions/{session_id}", json={"title": "Japan"})
        assert renamed.status_code == 200
        assert client.get(f"/sessions/{session_id}").json()["title"] == "Japan"

        assert client.delete(f"/sessions/{session_id}").status_code == 204
        missing = client.get(f"/sessions/{session_id}")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_other_owners_sessions_are_invisible(migrated_database_url: str) -> None:
    with _client(migrated_database_url, owner_id="alice") as alice:
        session_id = alice.post("/sessions", json={"title": "Private"}).json()["id"]

    with _client(migrated_database_url, owner_id="bob") as bob:
        assert bob.get("/sessions").json() == []
        assert bob.get(f"/sessions/{session_id}").status_code == 404
        assert bob.patch(f"/sessions/{session_id}", json={"title": "x"}).status_code == 404
        assert bob.delete(f"/sessions/{session_id}").status_code == 404

    with _client(migrated_database_url, owner_id="alice") as alice:
        assert alice.get(f"/sessions/{session_id}").json()["title"] == "Private"


def test_rejects_blank_title_and_unknown_session(migrated_database_url: str) -> None:
    with _client(migrated_database_url) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        blank = client.patch(f"/sessions/{session_id}", json={"title": "   "})
        unknown = client.delete(f"/sessions/{uuid.uuid4()}")

    assert blank.status_code == 422
    assert unknown.status_code == 404
