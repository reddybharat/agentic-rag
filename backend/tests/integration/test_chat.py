import json
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.models import DEFAULT_SESSION_TITLE
from app.main import create_app

UNREACHABLE_OLLAMA_URL = "http://127.0.0.1:1"


def _events(body: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


USAGE_SQL = "SELECT model_id, input_tokens, output_tokens FROM turn_usage"
type RunSql = Callable[[str], list[tuple[object, ...]]]


def test_chat_streams_answer_records_usage_and_titles_session(
    migrated_database_url: str, ollama_base_url: str, run_sql: RunSql
) -> None:
    settings = Settings(
        database_url=migrated_database_url, ollama_base_url=ollama_base_url, log_json=False
    )
    with TestClient(create_app(settings)) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"text": "What is the capital of France? Answer in one word."},
        )
        title = client.get(f"/sessions/{session_id}").json()["title"]

    assert response.status_code == 200
    events = _events(response.text)
    answer = "".join(str(data["text"]) for name, data in events if name == "token")
    assert "paris" in answer.lower()
    done_name, done = events[-1]
    assert done_name == "done"
    assert isinstance(done["output_tokens"], int)
    assert done["output_tokens"] > 0
    assert run_sql(USAGE_SQL) == [("qwen3-4b-smart", done["input_tokens"], done["output_tokens"])]
    assert title not in ("", DEFAULT_SESSION_TITLE)


def test_chat_emits_error_event_when_model_is_unreachable(
    migrated_database_url: str, run_sql: RunSql
) -> None:
    settings = Settings(
        database_url=migrated_database_url, ollama_base_url=UNREACHABLE_OLLAMA_URL, log_json=False
    )
    with TestClient(create_app(settings)) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        response = client.post(f"/sessions/{session_id}/messages", json={"text": "Hello"})

    assert response.status_code == 200
    assert [name for name, _ in _events(response.text)] == ["error"]
    assert run_sql(USAGE_SQL) == []


def test_chat_rejects_unknown_session_and_empty_message(migrated_database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=migrated_database_url))) as client:
        unknown = client.post(f"/sessions/{uuid.uuid4()}/messages", json={"text": "Hi"})
        session_id = client.post("/sessions", json={}).json()["id"]
        empty = client.post(f"/sessions/{session_id}/messages", json={"text": "  "})

    assert unknown.status_code == 404
    assert empty.status_code == 422
