import uuid

from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(Text)
    knowledge_base_ids: Mapped[str] = mapped_column(Text)
    result_count: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
