import httpx
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.domain.models import ModelSpec

PROVIDER_NAME = "ollama"


async def ping(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/version")
    response.raise_for_status()


class OllamaChatProvider:
    def __init__(self, base_url: str, timeout_s: float) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s

    def create(self, spec: ModelSpec) -> BaseChatModel:
        # ChatOllama ignores unknown fields, so a typo in models.yaml would vanish silently.
        unknown = spec.options.keys() - ChatOllama.model_fields.keys()
        if unknown:
            raise ValueError(f"Model {spec.id!r}: unknown ChatOllama options {sorted(unknown)}")
        return ChatOllama.model_validate(
            {
                **spec.options,
                "model": spec.model_name,
                "base_url": self._base_url,
                "client_kwargs": {"timeout": self._timeout_s},
            }
        )
