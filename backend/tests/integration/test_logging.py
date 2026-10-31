from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from app.core.config import Settings
from app.main import create_app

SAMPLE_PDF = Path(__file__).parents[1] / "fixtures" / "sample.pdf"
PDF_TYPE = "application/pdf"
TINY_UPLOAD_LIMIT = 100
UNREACHABLE_OLLAMA_URL = "http://127.0.0.1:1"
DOC_QUESTION = "What is the total budget for phase two of Project Halcyon?"


def _names(logs: list[MutableMapping[str, Any]]) -> list[object]:
    return [entry["event"] for entry in logs]


def test_upload_rejections_and_delete_are_logged_without_content(
    migrated_database_url: str,
) -> None:
    settings = Settings(database_url=migrated_database_url, max_upload_bytes=TINY_UPLOAD_LIMIT)
    app = create_app(settings)
    with capture_logs() as logs, TestClient(app) as client:
        client.post("/documents", files={"file": ("a.pdf", b"plain text", PDF_TYPE)})
        client.post("/documents", files={"file": ("b.pdf", SAMPLE_PDF.read_bytes(), PDF_TYPE)})
        client.delete("/documents/00000000-0000-0000-0000-000000000000")

    rejected = [e for e in logs if e["event"] == "upload_rejected"]
    assert [e["reason"] for e in rejected] == ["type", "size"]
    requests = [e for e in logs if e["event"] == "http_request"]
    assert [(e["method"], e["status"]) for e in requests] == [
        ("POST", 422),
        ("POST", 413),
        ("DELETE", 404),
    ]
    assert all(isinstance(e["duration_ms"], int) for e in requests)


def test_ingestion_and_chat_turn_log_the_key_events(
    migrated_database_url: str, ollama_base_url: str
) -> None:
    settings = Settings(database_url=migrated_database_url, ollama_base_url=ollama_base_url)
    app = create_app(settings)
    with capture_logs() as logs, TestClient(app) as client:
        client.post("/documents", files={"file": ("sample.pdf", SAMPLE_PDF.read_bytes(), PDF_TYPE)})
        session_id = client.post("/sessions", json={}).json()["id"]
        client.post(f"/sessions/{session_id}/messages", json={"text": DOC_QUESTION})

    names = _names(logs)
    for expected in (
        "upload_received",
        "ingestion_started",
        "ingestion_done",
        "turn_started",
        "tool_enabled",
        "preactivate",
        "skill_read",
        "tool_start",
        "search_done",
        "tool_end",
        "turn_done",
    ):
        assert expected in names, expected
    done = next(e for e in logs if e["event"] == "ingestion_done")
    assert done["pages"] == 4
    assert {"load_ms", "chunk_ms", "embed_ms", "store_ms", "total_ms"} <= done.keys()
    read = next(e for e in logs if e["event"] == "skill_read")
    assert read["source"] == "preactivate"
    assert all(DOC_QUESTION not in str(e.values()) for e in logs)


def test_failed_turn_is_logged_with_session_id(migrated_database_url: str) -> None:
    settings = Settings(database_url=migrated_database_url, ollama_base_url=UNREACHABLE_OLLAMA_URL)
    app = create_app(settings)
    with capture_logs() as logs, TestClient(app) as client:
        session_id = client.post("/sessions", json={}).json()["id"]
        client.post(f"/sessions/{session_id}/messages", json={"text": "Hello"})

    failed = [e for e in logs if e["event"] == "turn_failed"]
    assert [e["session_id"] for e in failed] == [session_id]
    assert failed[0]["log_level"] == "error"
