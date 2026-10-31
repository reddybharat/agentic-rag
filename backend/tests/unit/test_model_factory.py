import pytest
from langchain_ollama import ChatOllama

from app.core.config import Settings
from app.domain.models import ModelSpec
from app.infra.llm.model_factory import ModelFactory
from app.infra.llm.ollama import PROVIDER_NAME, OllamaChatProvider

BASE_URL = "http://localhost:11434"
TIMEOUT_S = 5.0
PROVIDERS = {PROVIDER_NAME: OllamaChatProvider(BASE_URL, TIMEOUT_S)}


def _spec(**overrides: object) -> ModelSpec:
    fields: dict[str, object] = {
        "id": "m",
        "provider": PROVIDER_NAME,
        "model_name": "qwen3:4b-instruct",
        "supports_tools": True,
    }
    return ModelSpec.model_validate(fields | overrides)


def test_catalog_builds_its_one_configured_model() -> None:
    settings = Settings(database_url="postgresql+asyncpg://unused")
    factory = ModelFactory.from_yaml(settings.models_config_path, PROVIDERS)

    model = factory.model
    assert isinstance(model, ChatOllama)
    assert (model.model, model.reasoning, model.num_ctx) == ("qwen3:4b-instruct", False, 8192)
    assert model.base_url == BASE_URL
    assert factory.spec.id == "qwen3-4b"


def test_rejects_zero_or_several_models() -> None:
    with pytest.raises(ValueError, match="exactly one model"):
        ModelFactory([], PROVIDERS)
    with pytest.raises(ValueError, match="exactly one model"):
        ModelFactory([_spec(), _spec(id="other")], PROVIDERS)


def test_rejects_unregistered_provider() -> None:
    with pytest.raises(ValueError, match="No chat provider"):
        ModelFactory([_spec(provider="gemini")], PROVIDERS)


def test_rejects_unknown_provider_option() -> None:
    with pytest.raises(ValueError, match="unknown ChatOllama options"):
        ModelFactory([_spec(options={"think": False})], PROVIDERS)
