from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Self

import structlog
import yaml
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.core.errors import UnknownModelError
from app.domain.models import ModelSpec
from app.domain.ports import ChatModelProvider

log = structlog.get_logger()


class _Catalog(BaseModel):
    models: list[ModelSpec]


class ModelFactory:
    """Builds every catalog model whose provider is registered; the first one is the default."""

    def __init__(
        self, specs: Sequence[ModelSpec], providers: Mapping[str, ChatModelProvider]
    ) -> None:
        ids = [spec.id for spec in specs]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate model ids in the catalog: {sorted(ids)}")
        for spec in specs:
            if spec.provider not in providers:
                log.warning("model_skipped", model_id=spec.id, provider=spec.provider)
        self._specs = [spec for spec in specs if spec.provider in providers]
        if not self._specs:
            raise ValueError("No catalog model has a registered provider")
        self._models = {spec.id: providers[spec.provider].create(spec) for spec in self._specs}

    @classmethod
    def from_yaml(cls, path: Path, providers: Mapping[str, ChatModelProvider]) -> Self:
        catalog = _Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        return cls(catalog.models, providers)

    @property
    def specs(self) -> list[ModelSpec]:
        return list(self._specs)

    @property
    def default(self) -> ModelSpec:
        return self._specs[0]

    def model(self, model_id: str) -> BaseChatModel:
        if model_id not in self._models:
            raise UnknownModelError(f"Unknown model {model_id!r}")
        return self._models[model_id]
