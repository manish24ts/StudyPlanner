"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schedule_status_enum = postgresql.ENUM(
        "PENDING", "DONE", name="schedulestatus", create_type=False
    )
    schedule_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("hours_per_day", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("plan_id", sa.Integer(),
                   sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "subtopics",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("topic_id", sa.Integer(),
                   sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("est_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("youtube_url", sa.String(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("subtopic_id", sa.Integer(),
                   sa.ForeignKey("subtopics.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("pass_threshold", sa.Float(), nullable=False, server_default="70.0"),
    )

    op.create_table(
        "schedule_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("plan_id", sa.Integer(),
                   sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subtopic_id", sa.Integer(),
                   sa.ForeignKey("subtopics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", schedule_status_enum, nullable=False, server_default="PENDING"),
        sa.UniqueConstraint("plan_id", "subtopic_id", name="uq_plan_subtopic_event"),
    )


def downgrade() -> None:
    op.drop_table("schedule_events")
    op.drop_table("quizzes")
    op.drop_table("subtopics")
    op.drop_table("topics")
    op.drop_table("plans")
    op.drop_table("users")
    sa.Enum(name="schedulestatus").drop(op.get_bind(), checkfirst=True)
