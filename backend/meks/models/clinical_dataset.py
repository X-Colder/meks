import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class ClinicalDataset(Base):
    __tablename__ = "clinical_datasets"

    name: Mapped[str] = mapped_column(String(256))
    original_filename: Mapped[str] = mapped_column(String(512))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_json: Mapped[str] = mapped_column(Text)
    rows_json: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
