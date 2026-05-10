import enum
import uuid

from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class Visibility(str, enum.Enum):
    private = "private"
    department = "department"
    public = "public"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    visibility: Mapped[Visibility] = mapped_column(Enum(Visibility), default=Visibility.department)
    department: Mapped[str | None] = mapped_column(String(128))
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    milvus_collection: Mapped[str] = mapped_column(String(128), unique=True)
