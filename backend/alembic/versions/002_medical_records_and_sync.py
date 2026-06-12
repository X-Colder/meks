"""medical records and sync tasks

Revision ID: 002
Revises: 001
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    severity_enum = sa.Enum("mild", "moderate", "severe", "critical", name="severity")
    treatment_outcome_enum = sa.Enum("cured", "improved", "unchanged", "deteriorated", "death", name="treatmentoutcome")
    extraction_status_enum = sa.Enum("pending", "extracting", "extracted", "failed", name="extractionstatus")
    kb_type_enum = sa.Enum("literature", "medical_record", name="kbtype")
    source_type_enum = sa.Enum("pmc", "arxiv", "rss", name="sourcetype")
    sync_status_enum = sa.Enum("idle", "running", "paused", "failed", name="syncstatus")

    severity_enum.create(op.get_bind(), checkfirst=True)
    treatment_outcome_enum.create(op.get_bind(), checkfirst=True)
    extraction_status_enum.create(op.get_bind(), checkfirst=True)
    kb_type_enum.create(op.get_bind(), checkfirst=True)
    source_type_enum.create(op.get_bind(), checkfirst=True)
    sync_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("documents", sa.Column("extraction_status", extraction_status_enum, nullable=True))

    op.add_column("knowledge_bases", sa.Column("kb_type", kb_type_enum, server_default="literature", nullable=False))
    op.add_column("knowledge_bases", sa.Column("field_template", sa.Text(), nullable=True))
    op.add_column("knowledge_bases", sa.Column("crawl_config", sa.Text(), nullable=True))

    op.create_table(
        "medical_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_name", sa.String(128), nullable=True),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("id_number", sa.String(32), nullable=True),
        sa.Column("occupation", sa.String(64), nullable=True),
        sa.Column("admission_date", sa.Date(), nullable=True),
        sa.Column("discharge_date", sa.Date(), nullable=True),
        sa.Column("hospital_days", sa.Integer(), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("attending_doctor", sa.String(128), nullable=True),
        sa.Column("admission_number", sa.String(64), nullable=True),
        sa.Column("primary_diagnosis", sa.Text(), nullable=True),
        sa.Column("icd10_code", sa.String(16), nullable=True),
        sa.Column("secondary_diagnoses", sa.Text(), nullable=True),
        sa.Column("severity", severity_enum, nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("procedures", sa.Text(), nullable=True),
        sa.Column("treatment_type", sa.String(64), nullable=True),
        sa.Column("treatment_outcome", treatment_outcome_enum, nullable=True),
        sa.Column("discharge_instructions", sa.Text(), nullable=True),
        sa.Column("follow_up", sa.Text(), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("present_illness", sa.Text(), nullable=True),
        sa.Column("past_history", sa.Text(), nullable=True),
        sa.Column("allergy_history", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_medical_records_icd10_code", "medical_records", ["icd10_code"])
    op.create_index("ix_medical_records_department", "medical_records", ["department"])

    op.create_table(
        "sync_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("watermark", sa.String(256), nullable=True),
        sa.Column("status", sync_status_enum, nullable=False),
        sa.Column("total_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("cron_expr", sa.String(64), nullable=True),
        sa.Column("target_kb_id", sa.Uuid(), sa.ForeignKey("knowledge_bases.id"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_tasks_status", "sync_tasks", ["status"])


def downgrade() -> None:
    op.drop_table("sync_tasks")
    op.drop_index("ix_medical_records_department", table_name="medical_records")
    op.drop_index("ix_medical_records_icd10_code", table_name="medical_records")
    op.drop_table("medical_records")
    op.drop_column("knowledge_bases", "crawl_config")
    op.drop_column("knowledge_bases", "field_template")
    op.drop_column("knowledge_bases", "kb_type")
    op.drop_column("documents", "extraction_status")
    op.execute("DROP TYPE IF EXISTS syncstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS kbtype")
    op.execute("DROP TYPE IF EXISTS extractionstatus")
    op.execute("DROP TYPE IF EXISTS treatmentoutcome")
    op.execute("DROP TYPE IF EXISTS severity")
