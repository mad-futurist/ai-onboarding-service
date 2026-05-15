"""phase1b courses lessons meetings

Revision ID: c8a3e2d5f102
Revises: b7f4e9c1d201
Create Date: 2026-05-14 14:00:00.000000

Adds the entities required for the next round of UI features:
- courses + lessons (mentor-curated, AI-generated, approval workflow)
- scheduled_meetings (basic meeting scheduling with optional Teams URL)

Strictly additive: no existing column, table, or row is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8a3e2d5f102"
down_revision: Union[str, Sequence[str], None] = "b7f4e9c1d201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("newcomer_id", sa.Integer(), nullable=True),
        sa.Column("mentor_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("generated_by_ai", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_document_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["onboarding_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_id"), "courses", ["id"], unique=False)
    op.create_index(op.f("ix_courses_plan_id"), "courses", ["plan_id"], unique=False)
    op.create_index(op.f("ix_courses_newcomer_id"), "courses", ["newcomer_id"], unique=False)
    op.create_index(op.f("ix_courses_mentor_id"), "courses", ["mentor_id"], unique=False)

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("infographic_url", sa.String(length=1024), nullable=True),
        sa.Column("infographic_kind", sa.String(length=50), nullable=True),
        sa.Column("infographic_source", sa.Text(), nullable=True),
        sa.Column("source_document_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lessons_id"), "lessons", ["id"], unique=False)
    op.create_index(op.f("ix_lessons_course_id"), "lessons", ["course_id"], unique=False)
    op.create_index("ix_lessons_course_id_index", "lessons", ["course_id", "index"], unique=False)

    op.create_table(
        "scheduled_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("newcomer_id", sa.Integer(), nullable=True),
        sa.Column("organizer_user_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("signal_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("agenda", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("teams_join_url", sa.String(length=1024), nullable=True),
        sa.Column("attendee_emails", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organizer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["onboarding_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["onboarding_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["ai_signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_meetings_id"), "scheduled_meetings", ["id"], unique=False)
    op.create_index(op.f("ix_scheduled_meetings_newcomer_id"), "scheduled_meetings", ["newcomer_id"], unique=False)
    op.create_index(op.f("ix_scheduled_meetings_organizer_user_id"), "scheduled_meetings", ["organizer_user_id"], unique=False)
    op.create_index(op.f("ix_scheduled_meetings_plan_id"), "scheduled_meetings", ["plan_id"], unique=False)
    op.create_index(op.f("ix_scheduled_meetings_task_id"), "scheduled_meetings", ["task_id"], unique=False)
    op.create_index(op.f("ix_scheduled_meetings_signal_id"), "scheduled_meetings", ["signal_id"], unique=False)
    op.create_index(
        "ix_scheduled_meetings_starts_at",
        "scheduled_meetings",
        ["starts_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_scheduled_meetings_starts_at", table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_signal_id"), table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_task_id"), table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_plan_id"), table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_organizer_user_id"), table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_newcomer_id"), table_name="scheduled_meetings")
    op.drop_index(op.f("ix_scheduled_meetings_id"), table_name="scheduled_meetings")
    op.drop_table("scheduled_meetings")

    op.drop_index("ix_lessons_course_id_index", table_name="lessons")
    op.drop_index(op.f("ix_lessons_course_id"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_id"), table_name="lessons")
    op.drop_table("lessons")

    op.drop_index(op.f("ix_courses_mentor_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_newcomer_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_plan_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_id"), table_name="courses")
    op.drop_table("courses")
