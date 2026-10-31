import pytest
from langchain_ollama import ChatOllama

from app.core.config import Settings
from app.domain.models import ModelSpec, Tier
from app.infra.llm.model_factory import ModelFactory
from app.infra.llm.ollama import PROVIDER_NAME, OllamaChatProvider

BASE_URL = "http://localhost:11434"
TIMEOUT_S = 5.0
PROVIDERS = {PROVIDER_NAME: OllamaChatProvider(BASE_URL, TIMEOUT_S)}


def _spec(tier: Tier, **overrides: object) -> ModelSpec:
    fields: dict[str, object] = {
        "id": f"m-{tier}",
        "provider": PROVIDER_NAME,
        "model_name": "qwen3:4b",
        "tier": tier,
        "supports_tools": True,
    }
    return ModelSpec.model_validate(fields | overrides)


def test_catalog_builds_one_configured_model_per_tier() -> None:
    settings = Settings(database_url="postgresql+asyncpg://unused")
    factory = ModelFactory.from_yaml(settings.models_config_path, PROVIDERS)

    fast, smart = factory.for_tier(Tier.FAST), factory.for_tier(Tier.SMART)
    assert isinstance(fast, ChatOllama)
    assert isinstance(smart, ChatOllama)
    assert (fast.model, fast.reasoning, fast.num_predict) == ("qwen3:4b", False, 256)
    assert (smart.model, smart.reasoning, smart.num_ctx) == ("qwen3:4b", False, 8192)
    assert fast.base_url == BASE_URL
    assert sorted(spec.tier for spec in factory.specs) == [Tier.FAST, Tier.SMART]


def test_rejects_missing_or_duplicate_tier() -> None:
    with pytest.raises(ValueError, match="exactly one model"):
        ModelFactory([_spec(Tier.FAST)], PROVIDERS)
    with pytest.raises(ValueError, match="exactly one model"):
        ModelFactory([_spec(Tier.FAST), _spec(Tier.FAST), _spec(Tier.SMART)], PROVIDERS)


def test_rejects_unregistered_provider() -> None:
    with pytest.raises(ValueError, match="No chat provider"):
        ModelFactory([_spec(Tier.FAST), _spec(Tier.SMART, provider="gemini")], PROVIDERS)


def test_rejects_unknown_provider_option() -> None:
    with pytest.raises(ValueError, match="unknown ChatOllama options"):
        ModelFactory([_spec(Tier.FAST), _spec(Tier.SMART, options={"think": False})], PROVIDERS)
