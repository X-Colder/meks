from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class PaperAnalysisResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    data_statistics_score: int | None = None
    data_statistics_verdict: str | None = None
    logic_consistency_score: int | None = None
    logic_consistency_verdict: str | None = None
    credibility_score: int | None = None
    credibility_verdict: str | None = None
    overall_risk_score: int | None = None
    risk_level: str | None = None
    data_statistics_findings: str | None = None
    logic_consistency_findings: str | None = None
    credibility_findings: str | None = None
    reproducibility_score: int | None = None
    reproducibility_verdict: str | None = None
    reproducibility_findings: str | None = None
    figure_consistency_score: int | None = None
    figure_consistency_verdict: str | None = None
    figure_consistency_findings: str | None = None
    citation_manipulation_score: int | None = None
    citation_manipulation_verdict: str | None = None
    citation_manipulation_findings: str | None = None
    overall_summary: str | None = None
    recommendations: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "document_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()
