import json
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

REJECTED_GROQ_KEY = "not-a-real-key"


def _events(body: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


QUESTION = "What is the capital of France? Answer in one word."
USAGE_SQL = "SELECT model_id, input_tokens, output_tokens FROM turn_usage"
type RunSql = Callable[[str], list[tuple[object, ...]]]


def test_chat_streams_answer_records_usage_and_titles_session(
    migrated_database_url: str, ollama_base_url: str, groq_api_key: str, run_sql: RunSql
) -> None:
    settings = Settings(
        database_url=migrated_database_url,
        ollama_base_url=ollama_base_url,
        groq_api_key=groq_api_key,
        log_json=False,
    )
    with TestClient(create_app(settings)) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"text": QUESTION},
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
    assert run_sql(USAGE_SQL) == [("qwen3.8-27b", done["input_tokens"], done["output_tokens"])]
    assert title == QUESTION


def test_chat_emits_error_event_when_the_model_call_fails(
    migrated_database_url: str, run_sql: RunSql
) -> None:
    settings = Settings(
        database_url=migrated_database_url, groq_api_key=REJECTED_GROQ_KEY, log_json=False
    )
    with TestClient(create_app(settings)) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        response = client.post(f"/sessions/{session_id}/messages", json={"text": "Hello"})

    assert response.status_code == 200
    assert [name for name, _ in _events(response.text)] == ["error"]
    assert run_sql(USAGE_SQL) == []


def test_chat_rejects_an_unknown_model_before_streaming(migrated_database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=migrated_database_url))) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        response = client.post(
            f"/sessions/{session_id}/messages", json={"text": "Hi", "model_id": "nope"}
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_model"


def test_chat_uses_the_default_and_the_selected_model(
    migrated_database_url: str,
    ollama_base_url: str,
    google_api_key: str,
    groq_api_key: str,
    run_sql: RunSql,
) -> None:
    settings = Settings(
        database_url=migrated_database_url,
        ollama_base_url=ollama_base_url,
        google_api_key=google_api_key,
        groq_api_key=groq_api_key,
        log_json=False,
    )
    with TestClient(create_app(settings)) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        default = client.post(f"/sessions/{session_id}/messages", json={"text": QUESTION})
        chosen = client.post(
            f"/sessions/{session_id}/messages",
            json={"text": QUESTION, "model_id": "qwen3.8-27b"},
        )

    assert [name for name, _ in _events(default.text)][-1] == "done"
    assert [name for name, _ in _events(chosen.text)][-1] == "done"
    assert [row[0] for row in run_sql("SELECT model_id FROM turn_usage ORDER BY created_at")] == [
        "gemini-3.5-flash-lite",
        "qwen3.8-27b",
    ]


def test_chat_rejects_unknown_session_and_empty_message(migrated_database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=migrated_database_url))) as client:
        unknown = client.post(f"/sessions/{uuid.uuid4()}/messages", json={"text": "Hi"})
        session_id = client.post("/sessions", json={}).json()["id"]
        empty = client.post(f"/sessions/{session_id}/messages", json={"text": "  "})

    assert unknown.status_code == 404
    assert empty.status_code == 422
