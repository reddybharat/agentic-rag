from pydantic import BaseModel

from app.domain.models import Tier


class ModelOut(BaseModel):
    id: str
    provider: str
    model_name: str
    tier: Tier
    supports_tools: bool
