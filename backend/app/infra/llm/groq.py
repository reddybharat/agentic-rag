from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

from app.domain.models import ModelSpec

PROVIDER_NAME = "groq"


class GroqChatProvider:
    def __init__(self, api_key: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def create(self, spec: ModelSpec) -> BaseChatModel:
        # ChatGroq ignores unknown fields, so a typo in models.yaml would vanish silently.
        unknown = spec.options.keys() - ChatGroq.model_fields.keys()
        if unknown:
            raise ValueError(f"Model {spec.id!r}: unknown ChatGroq options {sorted(unknown)}")
        return ChatGroq.model_validate(
            {
                **spec.options,
                "model_name": spec.model_name,
                "groq_api_key": self._api_key,
                "request_timeout": self._timeout_s,
            }
        )
