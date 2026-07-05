from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class ClinicalColumn(BaseModel):
    name: str
    label: str
    inferred_type: str
    missing_count: int
    missing_rate: float
    unique_count: int
    role: str | None = None


class ClinicalDatasetResponse(BaseModel):
    id: UUID
    name: str
    original_filename: str
    row_count: int
    column_count: int
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "owner_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()


class ClinicalDatasetDetail(ClinicalDatasetResponse):
    columns: list[ClinicalColumn]
    preview_rows: list[dict]


class ClinicalStatsResponse(BaseModel):
    columns: list[ClinicalColumn]
    numeric_summary: dict
    categorical_summary: dict
    missing_summary: list[dict]


class ResearchSuggestionRequest(BaseModel):
    clinical_question: str | None = None
    exposure: str | None = None
    outcome: str | None = None


class ClinicalTimelineEvent(BaseModel):
    patient_id: str
    date: str | None = None
    event_type: str
    title: str
    details: dict


class ClinicalPatientSummary(BaseModel):
    patient_id: str
    age: str | None = None
    sex: str | None = None
    first_visit: str | None = None
    last_visit: str | None = None
    encounter_count: int
    diagnosis_count: int
    diagnoses: list[str]
    risk_flags: list[str]


class ClinicalLongitudinalResponse(BaseModel):
    patient_id_column: str | None = None
    date_column: str | None = None
    diagnosis_columns: list[str]
    patient_count: int
    event_count: int
    patients: list[ClinicalPatientSummary]
    events: list[ClinicalTimelineEvent]
    top_diagnoses: list[dict]
    cohort_preview: list[dict]
    warnings: list[str]
