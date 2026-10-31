from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    owner_id: str
