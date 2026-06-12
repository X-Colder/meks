import enum
import uuid
from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from meks.models.base import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PaperAnalysis(Base):
    __tablename__ = "paper_analyses"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), unique=True)
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.pending)
    data_statistics_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_statistics_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logic_consistency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logic_consistency_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credibility_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    overall_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel), nullable=True)
    data_statistics_findings: Mapped[str | None] = mapped_column(Text)
    logic_consistency_findings: Mapped[str | None] = mapped_column(Text)
    credibility_findings: Mapped[str | None] = mapped_column(Text)
    reproducibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reproducibility_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reproducibility_findings: Mapped[str | None] = mapped_column(Text)
    figure_consistency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    figure_consistency_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    figure_consistency_findings: Mapped[str | None] = mapped_column(Text)
    citation_manipulation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_manipulation_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    citation_manipulation_findings: Mapped[str | None] = mapped_column(Text)
    overall_summary: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    analyzed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
