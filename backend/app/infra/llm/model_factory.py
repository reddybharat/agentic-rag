from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Self

import yaml
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.domain.models import ModelSpec, Tier
from app.domain.ports import ChatModelProvider


class _Catalog(BaseModel):
    models: list[ModelSpec]


class ModelFactory:
    """Registry of chat models built from the catalog by their provider; one model per tier."""

    def __init__(
        self, specs: Sequence[ModelSpec], providers: Mapping[str, ChatModelProvider]
    ) -> None:
        tier_counts = Counter(spec.tier for spec in specs)
        invalid_tiers = {tier: tier_counts[tier] for tier in Tier if tier_counts[tier] != 1}
        if invalid_tiers:
            raise ValueError(f"Each tier needs exactly one model, got {invalid_tiers}")
        unknown = {spec.provider for spec in specs} - providers.keys()
        if unknown:
            raise ValueError(f"No chat provider registered for {sorted(unknown)}")

        self._specs = list(specs)
        self._specs_by_tier = {spec.tier: spec for spec in specs}
        self._models = {spec.tier: providers[spec.provider].create(spec) for spec in specs}

    @classmethod
    def from_yaml(cls, path: Path, providers: Mapping[str, ChatModelProvider]) -> Self:
        catalog = _Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        return cls(catalog.models, providers)

    @property
    def specs(self) -> list[ModelSpec]:
        return list(self._specs)

    def spec_for(self, tier: Tier) -> ModelSpec:
        return self._specs_by_tier[tier]

    def for_tier(self, tier: Tier) -> BaseChatModel:
        return self._models[tier]
