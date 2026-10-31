from pydantic import BaseModel


class ModelOut(BaseModel):
    id: str
    provider: str
    model_name: str
    supports_tools: bool
