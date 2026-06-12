from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class PaperCreate(BaseModel):
    title: str = "未命名论文"
    abstract: str | None = None
    target_journal: str | None = None


class PaperUpdate(BaseModel):
    title: str | None = None
    abstract: str | None = None
    status: str | None = None
    keywords: str | None = None
    target_journal: str | None = None


class PaperResponse(BaseModel):
    id: UUID
    title: str
    abstract: str | None
    status: str
    owner_id: UUID
    keywords: str | None
    target_journal: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "owner_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()


class BlockCreate(BaseModel):
    block_type: str = "text"
    content: str = ""
    sort_order: int = 0
    source_type: str | None = None
    source_id: str | None = None
    extra: str | None = None


class BlockUpdate(BaseModel):
    content: str | None = None
    sort_order: int | None = None
    block_type: str | None = None
    extra: str | None = None


class BlockResponse(BaseModel):
    id: UUID
    paper_id: UUID
    block_type: str
    content: str
    sort_order: int
    source_type: str | None
    source_id: str | None
    extra: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "paper_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()


class PaperDetailResponse(PaperResponse):
    blocks: list[BlockResponse] = []


class ImportBlockRequest(BaseModel):
    source_type: str
    source_id: str
    content: str
    block_type: str = "text"


class ReorderBlocksRequest(BaseModel):
    block_ids: list[str]


class PaperExportRequest(BaseModel):
    watermark_text: str | None = None
