from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.models import Tier
from app.infra.embeddings.ollama import OllamaEmbedder
from app.infra.llm.model_factory import ModelFactory
from app.infra.llm.ollama import PROVIDER_NAME, OllamaChatProvider
from app.main import create_app

UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nothing"
LLM_TIMEOUT_S = 120.0


def test_list_models_returns_catalog_without_options() -> None:
    app = create_app(Settings(database_url=UNREACHABLE_DATABASE_URL, log_json=False))
    with TestClient(app) as client:
        response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "qwen3-4b-fast",
            "provider": "ollama",
            "model_name": "qwen3:4b-instruct",
            "tier": "fast",
            "supports_tools": True,
        },
        {
            "id": "qwen3-4b-smart",
            "provider": "ollama",
            "model_name": "qwen3:4b-instruct",
            "tier": "smart",
            "supports_tools": True,
        },
    ]


async def test_fast_model_answers_via_ollama(ollama_base_url: str) -> None:
    settings = Settings(database_url=UNREACHABLE_DATABASE_URL, ollama_base_url=ollama_base_url)
    factory = ModelFactory.from_yaml(
        settings.models_config_path,
        {PROVIDER_NAME: OllamaChatProvider(ollama_base_url, LLM_TIMEOUT_S)},
    )

    reply = await factory.for_tier(Tier.FAST).ainvoke("Reply with the single word: pong")

    assert "pong" in str(reply.content).lower()


async def test_embedder_returns_configured_dimension(ollama_base_url: str) -> None:
    settings = Settings(database_url=UNREACHABLE_DATABASE_URL, ollama_base_url=ollama_base_url)
    embedder = OllamaEmbedder(
        ollama_base_url, settings.embedding_model, settings.embedding_dim, LLM_TIMEOUT_S
    )

    query = await embedder.embed_query("What is pgvector?")
    chunks = await embedder.embed_documents(["pgvector adds vector search to Postgres.", "Hi"])

    assert len(query) == settings.embedding_dim
    assert [len(c) for c in chunks] == [settings.embedding_dim] * 2
