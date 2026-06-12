"""paper collaboration

Revision ID: 004
Revises: 003
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    paper_status_enum = sa.Enum("draft", "review", "published", name="paperstatus")
    block_type_enum = sa.Enum("text", "heading", "table", "image", "citation", "divider", name="blocktype")

    paper_status_enum.create(op.get_bind(), checkfirst=True)
    block_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "papers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("status", paper_status_enum, nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("target_journal", sa.String(256), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_papers_owner_id", "papers", ["owner_id"])

    op.create_table(
        "paper_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("paper_id", sa.UUID(), nullable=False),
        sa.Column("block_type", block_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=True),
        sa.Column("source_id", sa.String(256), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_blocks_paper_id", "paper_blocks", ["paper_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_blocks_paper_id", table_name="paper_blocks")
    op.drop_table("paper_blocks")
    op.drop_index("ix_papers_owner_id", table_name="papers")
    op.drop_table("papers")
    sa.Enum(name="blocktype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="paperstatus").drop(op.get_bind(), checkfirst=True)
