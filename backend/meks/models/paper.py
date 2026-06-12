import enum
import uuid
from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from meks.models.base import Base


class PaperStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    published = "published"


class BlockType(str, enum.Enum):
    text = "text"
    heading = "heading"
    table = "table"
    image = "image"
    citation = "citation"
    divider = "divider"


class Paper(Base):
    __tablename__ = "papers"

    title: Mapped[str] = mapped_column(String(512), default="未命名论文")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PaperStatus] = mapped_column(Enum(PaperStatus), default=PaperStatus.draft)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_journal: Mapped[str | None] = mapped_column(String(256), nullable=True)


class PaperBlock(Base):
    __tablename__ = "paper_blocks"

    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    block_type: Mapped[BlockType] = mapped_column(Enum(BlockType))
    content: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
