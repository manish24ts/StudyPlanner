"""learning resources columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subtopics", sa.Column("youtube_title", sa.String(), nullable=True))
    op.add_column("subtopics", sa.Column("youtube_channel", sa.String(), nullable=True))
    op.add_column("subtopics", sa.Column("blog_links", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("subtopics", "blog_links")
    op.drop_column("subtopics", "youtube_channel")
    op.drop_column("subtopics", "youtube_title")
