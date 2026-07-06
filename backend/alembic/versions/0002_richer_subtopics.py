"""richer subtopics

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("subtopics", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("subtopics", sa.Column("key_points", sa.JSON(), nullable=True))
    op.add_column("subtopics", sa.Column("study_tip", sa.Text(), nullable=True))
    op.add_column(
        "subtopics",
        sa.Column("is_supplementary", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("subtopics", "is_supplementary")
    op.drop_column("subtopics", "study_tip")
    op.drop_column("subtopics", "key_points")
    op.drop_column("subtopics", "description")
    op.drop_column("topics", "summary")
