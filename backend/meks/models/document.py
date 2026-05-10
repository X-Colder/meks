import enum
import uuid
from datetime import date

from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class FileType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    doc = "doc"
    xml = "xml"
    txt = "txt"
    markdown = "markdown"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[FileType] = mapped_column(Enum(FileType))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(1024))

    authors: Mapped[str | None] = mapped_column(Text)
    journal: Mapped[str | None] = mapped_column(String(256))
    doi: Mapped[str | None] = mapped_column(String(256), index=True)
    publication_date: Mapped[date | None] = mapped_column(nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(Text)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.uploaded
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
