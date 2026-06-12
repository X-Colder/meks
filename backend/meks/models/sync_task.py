import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class SourceType(str, enum.Enum):
    pmc = "pmc"
    arxiv = "arxiv"
    rss = "rss"
    biorxiv = "biorxiv"
    europepmc = "europepmc"
    semantic_scholar = "semantic_scholar"


class SyncStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    paused = "paused"
    failed = "failed"


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    name: Mapped[str] = mapped_column(String(256))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    config: Mapped[str] = mapped_column(Text)
    watermark: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.idle, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cron_expr: Mapped[str | None] = mapped_column(String(64))
    target_kb_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
