from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class ChatSessionCreate(BaseModel):
    title: str | None = None
    knowledge_base_ids: list[str]


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    knowledge_base_ids: str
    message_count: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    source_chunks: str | None
    llm_provider: str | None
    model_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()
