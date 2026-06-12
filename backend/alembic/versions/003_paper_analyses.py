"""paper analyses

Revision ID: 003
Revises: 002
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    analysis_status_enum = sa.Enum("pending", "analyzing", "completed", "failed", name="analysisstatus")
    risk_level_enum = sa.Enum("low", "medium", "high", "critical", name="risklevel")

    analysis_status_enum.create(op.get_bind(), checkfirst=True)
    risk_level_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "paper_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("status", analysis_status_enum, nullable=False),
        sa.Column("data_statistics_score", sa.Integer(), nullable=True),
        sa.Column("logic_consistency_score", sa.Integer(), nullable=True),
        sa.Column("credibility_score", sa.Integer(), nullable=True),
        sa.Column("overall_risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", risk_level_enum, nullable=True),
        sa.Column("data_statistics_findings", sa.Text(), nullable=True),
        sa.Column("logic_consistency_findings", sa.Text(), nullable=True),
        sa.Column("credibility_findings", sa.Text(), nullable=True),
        sa.Column("overall_summary", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("analyzed_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["analyzed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )


def downgrade() -> None:
    op.drop_table("paper_analyses")
    sa.Enum(name="risklevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="analysisstatus").drop(op.get_bind(), checkfirst=True)
