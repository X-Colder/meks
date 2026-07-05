import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class PaperReadingCard(Base):
    __tablename__ = "paper_reading_cards"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
    )
    content: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
