from pydantic import BaseModel


class MedicalRecordResponse(BaseModel):
    id: str
    document_id: str
    patient_name: str | None
    gender: str | None
    age: int | None
    department: str | None
    primary_diagnosis: str | None
    icd10_code: str | None
    severity: str | None
    treatment_outcome: str | None
    admission_date: str | None
    discharge_date: str | None
    hospital_days: int | None
    medications: str | None
    procedures: str | None
    chief_complaint: str | None
    created_at: str

    model_config = {"from_attributes": True}


class MedicalRecordListResponse(BaseModel):
    items: list[MedicalRecordResponse]
    total: int
    page: int
    page_size: int
