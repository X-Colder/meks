from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class ReadingCardUpsert(BaseModel):
    content: str


class ReadingCardResponse(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    generated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "document_id", "generated_by")
    def serialize_uuid(self, v: UUID | None) -> str | None:
        return str(v) if v else None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()
