from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Tier(StrEnum):
    FAST = "fast"
    SMART = "smart"


class ModelSpec(BaseModel):
    """One entry of the chat model catalog (`config/models.yaml`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    provider: str
    model_name: str
    tier: Tier
    supports_tools: bool
    options: dict[str, str | int | float | bool] = {}
