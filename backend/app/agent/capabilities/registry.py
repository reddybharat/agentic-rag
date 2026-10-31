from collections.abc import Sequence

from app.domain.models import Capability
from app.domain.ports import CapabilityProvider


class CapabilityRegistry:
    """All capabilities from every provider, discovered once at agent build."""

    def __init__(self, providers: Sequence[CapabilityProvider]) -> None:
        self._by_name: dict[str, Capability] = {}
        for provider in providers:
            for capability in provider.discover():
                if capability.name in self._by_name:
                    raise ValueError(f"Duplicate capability {capability.name!r}")
                self._by_name[capability.name] = capability

    @property
    def capabilities(self) -> list[Capability]:
        return list(self._by_name.values())

    def get(self, name: str) -> Capability | None:
        return self._by_name.get(name)
