from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.domain.models import ModelSpec

PROVIDER_NAME = "gemini"


class GeminiChatProvider:
    def __init__(self, api_key: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def create(self, spec: ModelSpec) -> BaseChatModel:
        # Unknown fields would be rejected or ignored depending on the version; fail at startup.
        unknown = spec.options.keys() - ChatGoogleGenerativeAI.model_fields.keys()
        if unknown:
            raise ValueError(
                f"Model {spec.id!r}: unknown ChatGoogleGenerativeAI options {sorted(unknown)}"
            )
        return ChatGoogleGenerativeAI.model_validate(
            {
                **spec.options,
                "model": spec.model_name,
                "google_api_key": self._api_key,
                "timeout": self._timeout_s,
            }
        )
