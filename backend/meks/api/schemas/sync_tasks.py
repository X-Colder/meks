from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class SyncTaskCreate(BaseModel):
    name: str
    source_type: str
    config: dict
    cron_expr: str | None = None
    target_kb_id: str


class SyncTaskUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    cron_expr: str | None = None
    status: str | None = None


class SyncTaskResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    config: str
    watermark: str | None
    status: str
    total_count: int
    processed_count: int
    last_sync_at: datetime | None
    cron_expr: str | None
    target_kb_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "target_kb_id", "created_by")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()

    @field_serializer("last_sync_at")
    def serialize_opt_dt(self, v: datetime | None) -> str | None:
        return v.isoformat() if v else None


class SyncTaskListResponse(BaseModel):
    items: list[SyncTaskResponse]
    total: int
