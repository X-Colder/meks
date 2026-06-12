from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "department"
    department: str | None = None
    kb_type: str = "literature"
    field_template: dict | None = None
    crawl_config: dict | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    visibility: str
    department: str | None
    document_count: int
    owner_id: UUID
    created_at: datetime
    kb_type: str
    field_template: str | None
    crawl_config: str | None

    model_config = {"from_attributes": True}

    @field_serializer("id", "owner_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()
