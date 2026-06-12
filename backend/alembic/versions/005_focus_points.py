"""focus points

Revision ID: 005
Revises: 004
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "focus_points",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("max_results", sa.Integer(), nullable=False),
        sa.Column("cron_expr", sa.String(64), nullable=True),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=True),
        sa.Column("sync_task_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["sync_task_id"], ["sync_tasks.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_focus_points_owner_id", "focus_points", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_focus_points_owner_id", table_name="focus_points")
    op.drop_table("focus_points")
