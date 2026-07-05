from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    authors: str | None
    journal: str | None
    doi: str | None
    publication_date: date | None
    abstract: str | None
    keywords: str | None
    chunk_count: int
    knowledge_base_id: UUID
    uploaded_by: UUID
    created_at: datetime
    error_message: str | None = None
    analysis_status: str | None = None
    analysis_risk_score: int | None = None
    risk_level: str | None = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "knowledge_base_id", "uploaded_by")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()

    @field_serializer("publication_date")
    def serialize_date(self, v: date | None) -> str | None:
        return v.isoformat() if v else None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentContentResponse(BaseModel):
    id: UUID
    title: str
    authors: str | None
    abstract: str | None
    content: str
    status: str
    publication_date: date | None

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("publication_date")
    def serialize_date(self, v: date | None) -> str | None:
        return v.isoformat() if v else None
