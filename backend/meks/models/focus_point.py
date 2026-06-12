import uuid

from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class FocusPoint(Base):
    __tablename__ = "focus_points"

    name: Mapped[str] = mapped_column(String(256))
    query: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), default="pmc")
    max_results: Mapped[int] = mapped_column(Integer, default=50)
    cron_expr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=True)
    sync_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sync_tasks.id"), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
