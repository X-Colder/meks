"""clinical datasets

Revision ID: 007
Revises: 006
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("columns_json", sa.Text(), nullable=False),
        sa.Column("rows_json", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_datasets_owner_id", "clinical_datasets", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_clinical_datasets_owner_id", table_name="clinical_datasets")
    op.drop_table("clinical_datasets")
