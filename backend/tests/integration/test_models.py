from fastapi.testclient import TestClient

from app.core.config import Settings
from app.infra.embeddings.ollama import OllamaEmbedder
from app.infra.llm import gemini, groq
from app.infra.llm.model_factory import ModelFactory
from app.main import create_app

UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nothing"
LLM_TIMEOUT_S = 120.0


def test_list_models_without_a_gemini_key_offers_only_groq() -> None:
    app = create_app(Settings(database_url=UNREACHABLE_DATABASE_URL, log_json=False))
    with TestClient(app) as client:
        response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "qwen3.8-27b",
            "provider": "groq",
            "model_name": "qwen/qwen3.8-27b",
            "supports_tools": True,
        }
    ]


def test_list_models_with_a_key_lists_gemini_first_without_options() -> None:
    settings = Settings(
        database_url=UNREACHABLE_DATABASE_URL, google_api_key="not-a-real-key", log_json=False
    )
    with TestClient(create_app(settings)) as client:
        models = client.get("/models").json()

    assert [m["id"] for m in models] == ["gemini-3.5-flash-lite", "gemini-3.6-flash", "qwen3.8-27b"]
    assert models[0] == {
        "id": "gemini-3.5-flash-lite",
        "provider": "gemini",
        "model_name": "gemini-3.5-flash-lite",
        "supports_tools": True,
    }


async def test_groq_model_answers(groq_api_key: str) -> None:
    settings = Settings(database_url=UNREACHABLE_DATABASE_URL)
    factory = ModelFactory.from_yaml(
        settings.models_config_path,
        {groq.PROVIDER_NAME: groq.GroqChatProvider(groq_api_key, LLM_TIMEOUT_S)},
    )

    reply = await factory.model(factory.default.id).ainvoke("Reply with the single word: pong")

    assert "pong" in reply.text.lower()


async def test_gemini_model_answers(google_api_key: str) -> None:
    settings = Settings(database_url=UNREACHABLE_DATABASE_URL)
    factory = ModelFactory.from_yaml(
        settings.models_config_path,
        {gemini.PROVIDER_NAME: gemini.GeminiChatProvider(google_api_key, LLM_TIMEOUT_S)},
    )

    reply = await factory.model(factory.default.id).ainvoke("Reply with the single word: pong")

    assert "pong" in reply.text.lower()


async def test_embedder_returns_configured_dimension(ollama_base_url: str) -> None:
    settings = Settings(database_url=UNREACHABLE_DATABASE_URL, ollama_base_url=ollama_base_url)
    embedder = OllamaEmbedder(
        ollama_base_url, settings.embedding_model, settings.embedding_dim, LLM_TIMEOUT_S
    )

    query = await embedder.embed_query("What is pgvector?")
    chunks = await embedder.embed_documents(["pgvector adds vector search to Postgres.", "Hi"])

    assert len(query) == settings.embedding_dim
    assert [len(c) for c in chunks] == [settings.embedding_dim] * 2
