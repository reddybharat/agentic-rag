import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.models import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    page_count: int | None
    status: DocumentStatus
    error: str | None
    created_at: datetime
