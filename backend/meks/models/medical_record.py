import enum
import uuid
from datetime import date

from sqlalchemy import String, Text, ForeignKey, Enum, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class Severity(str, enum.Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    critical = "critical"


class TreatmentOutcome(str, enum.Enum):
    cured = "cured"
    improved = "improved"
    unchanged = "unchanged"
    deteriorated = "deteriorated"
    death = "death"


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )

    patient_name: Mapped[str | None] = mapped_column(String(128))
    gender: Mapped[str | None] = mapped_column(String(16))
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    id_number: Mapped[str | None] = mapped_column(String(32))
    occupation: Mapped[str | None] = mapped_column(String(64))

    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hospital_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department: Mapped[str | None] = mapped_column(String(128))
    attending_doctor: Mapped[str | None] = mapped_column(String(128))
    admission_number: Mapped[str | None] = mapped_column(String(64))

    primary_diagnosis: Mapped[str | None] = mapped_column(Text)
    icd10_code: Mapped[str | None] = mapped_column(String(16), index=True)
    secondary_diagnoses: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[Severity | None] = mapped_column(Enum(Severity), nullable=True)

    medications: Mapped[str | None] = mapped_column(Text)
    procedures: Mapped[str | None] = mapped_column(Text)
    treatment_type: Mapped[str | None] = mapped_column(String(64))
    treatment_outcome: Mapped[TreatmentOutcome | None] = mapped_column(
        Enum(TreatmentOutcome), nullable=True
    )

    discharge_instructions: Mapped[str | None] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text)

    chief_complaint: Mapped[str | None] = mapped_column(Text)
    present_illness: Mapped[str | None] = mapped_column(Text)
    past_history: Mapped[str | None] = mapped_column(Text)
    allergy_history: Mapped[str | None] = mapped_column(Text)
