from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Self

import yaml
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.domain.models import ModelSpec
from app.domain.ports import ChatModelProvider


class _Catalog(BaseModel):
    models: list[ModelSpec]


class ModelFactory:
    """Builds the catalog's one chat model through its registered provider."""

    def __init__(
        self, specs: Sequence[ModelSpec], providers: Mapping[str, ChatModelProvider]
    ) -> None:
        if len(specs) != 1:
            raise ValueError(f"The catalog needs exactly one model, got {len(specs)}")
        spec = specs[0]
        if spec.provider not in providers:
            raise ValueError(f"No chat provider registered for {spec.provider!r}")
        self._spec = spec
        self._model = providers[spec.provider].create(spec)

    @classmethod
    def from_yaml(cls, path: Path, providers: Mapping[str, ChatModelProvider]) -> Self:
        catalog = _Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        return cls(catalog.models, providers)

    @property
    def spec(self) -> ModelSpec:
        return self._spec

    @property
    def model(self) -> BaseChatModel:
        return self._model
