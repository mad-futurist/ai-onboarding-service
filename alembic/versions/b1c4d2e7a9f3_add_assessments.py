"""add assessments tables

Revision ID: b1c4d2e7a9f3
Revises: f9c2d7e4a1b5
Create Date: 2026-05-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c4d2e7a9f3"
down_revision: Union[str, Sequence[str], None] = "f9c2d7e4a1b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("newcomer_id", sa.Integer(), nullable=True),
        sa.Column("mentor_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("mentor_notes", sa.Text(), nullable=True),
        sa.Column("role_context", sa.Text(), nullable=True),
        sa.Column("source_document_ids", sa.JSON(), nullable=True),
        sa.Column("generated_by_ai", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("used_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"]),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessments_id"), "assessments", ["id"], unique=False)
    op.create_index(op.f("ix_assessments_newcomer_id"), "assessments", ["newcomer_id"], unique=False)
    op.create_index(op.f("ix_assessments_mentor_id"), "assessments", ["mentor_id"], unique=False)

    op.create_table(
        "assessment_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("skill_tag", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_questions_id"), "assessment_questions", ["id"], unique=False)
    op.create_index(
        op.f("ix_assessment_questions_assessment_id"),
        "assessment_questions",
        ["assessment_id"],
        unique=False,
    )

    op.create_table(
        "assessment_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("newcomer_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_submissions_id"), "assessment_submissions", ["id"], unique=False)
    op.create_index(
        op.f("ix_assessment_submissions_assessment_id"),
        "assessment_submissions",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_submissions_newcomer_id"),
        "assessment_submissions",
        ["newcomer_id"],
        unique=False,
    )

    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("selected_option_ids", sa.JSON(), nullable=True),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("mentor_score", sa.Float(), nullable=True),
        sa.Column("mentor_feedback", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["submission_id"], ["assessment_submissions.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_answers_id"), "assessment_answers", ["id"], unique=False)
    op.create_index(
        op.f("ix_assessment_answers_submission_id"),
        "assessment_answers",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_answers_question_id"),
        "assessment_answers",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_answers_question_id"), table_name="assessment_answers")
    op.drop_index(op.f("ix_assessment_answers_submission_id"), table_name="assessment_answers")
    op.drop_index(op.f("ix_assessment_answers_id"), table_name="assessment_answers")
    op.drop_table("assessment_answers")

    op.drop_index(op.f("ix_assessment_submissions_newcomer_id"), table_name="assessment_submissions")
    op.drop_index(op.f("ix_assessment_submissions_assessment_id"), table_name="assessment_submissions")
    op.drop_index(op.f("ix_assessment_submissions_id"), table_name="assessment_submissions")
    op.drop_table("assessment_submissions")

    op.drop_index(op.f("ix_assessment_questions_assessment_id"), table_name="assessment_questions")
    op.drop_index(op.f("ix_assessment_questions_id"), table_name="assessment_questions")
    op.drop_table("assessment_questions")

    op.drop_index(op.f("ix_assessments_mentor_id"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_newcomer_id"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_id"), table_name="assessments")
    op.drop_table("assessments")
