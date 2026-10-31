import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.config import Settings
from app.core.errors import UnknownModelError
from app.domain.models import ModelSpec
from app.infra.llm import gemini, groq
from app.infra.llm.model_factory import ModelFactory

TIMEOUT_S = 5.0
FAKE_KEY = "not-a-real-key"  # building a chat client makes no network call
GROQ_ONLY = {groq.PROVIDER_NAME: groq.GroqChatProvider(FAKE_KEY, TIMEOUT_S)}
BOTH = GROQ_ONLY | {gemini.PROVIDER_NAME: gemini.GeminiChatProvider(FAKE_KEY, TIMEOUT_S)}
CATALOG_PATH = Settings(database_url="postgresql+asyncpg://unused").models_config_path


def _spec(**overrides: object) -> ModelSpec:
    fields: dict[str, object] = {
        "id": "m",
        "provider": groq.PROVIDER_NAME,
        "model_name": "qwen/qwen3.8-27b",
        "supports_tools": True,
    }
    return ModelSpec.model_validate(fields | overrides)


def test_catalog_builds_every_model_and_the_first_is_the_default() -> None:
    factory = ModelFactory.from_yaml(CATALOG_PATH, BOTH)

    assert [s.id for s in factory.specs] == [
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "qwen3.8-27b",
    ]
    assert factory.default.id == "gemini-3.5-flash-lite"
    assert isinstance(factory.model("gemini-3.6-flash"), ChatGoogleGenerativeAI)
    hosted = factory.model("qwen3.8-27b")
    assert isinstance(hosted, ChatGroq)
    assert (hosted.model_name, hosted.request_timeout) == ("qwen/qwen3.8-27b", TIMEOUT_S)


def test_models_of_an_unregistered_provider_are_skipped() -> None:
    factory = ModelFactory.from_yaml(CATALOG_PATH, GROQ_ONLY)

    assert [s.id for s in factory.specs] == ["qwen3.8-27b"]
    assert factory.default.id == "qwen3.8-27b"


def test_rejects_unknown_model_id() -> None:
    with pytest.raises(UnknownModelError, match="nope"):
        ModelFactory.from_yaml(CATALOG_PATH, BOTH).model("nope")


def test_rejects_empty_or_duplicate_catalog() -> None:
    with pytest.raises(ValueError, match="registered provider"):
        ModelFactory([_spec(provider="gemini")], GROQ_ONLY)
    with pytest.raises(ValueError, match="Duplicate"):
        ModelFactory([_spec(), _spec()], GROQ_ONLY)


@pytest.mark.parametrize("provider", [groq.PROVIDER_NAME, gemini.PROVIDER_NAME])
def test_rejects_unknown_provider_option(provider: str) -> None:
    with pytest.raises(ValueError, match=r"unknown .* options"):
        ModelFactory([_spec(provider=provider, options={"nonsense_option": 1})], BOTH)
