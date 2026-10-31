from dataclasses import dataclass
from typing import Annotated, NotRequired

from langchain.agents.middleware.types import AgentState


def _merge_names(current: list[str], new: list[str]) -> list[str]:
    return current + [name for name in new if name not in current]


class CapabilityState(AgentState[None]):
    # Per run only: turns are stateless, so every turn starts with none active.
    active_capabilities: NotRequired[Annotated[list[str], _merge_names]]


@dataclass(frozen=True)
class AgentContext:
    owner_id: str
