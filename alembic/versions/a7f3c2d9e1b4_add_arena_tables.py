"""add customer training arena tables

Revision ID: a7f3c2d9e1b4
Revises: e2b7a4c9d6f1
Create Date: 2026-05-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7f3c2d9e1b4"
down_revision: Union[str, Sequence[str], None] = "e2b7a4c9d6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "arena_scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=True),
        sa.Column("audience_newcomer_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("conversation_type", sa.String(length=50), nullable=False, server_default="discovery"),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("persona", sa.JSON(), nullable=False),
        sa.Column("goal_text", sa.Text(), nullable=True),
        sa.Column("success_criteria", sa.JSON(), nullable=True),
        sa.Column("kb_source_ids", sa.JSON(), nullable=True),
        sa.Column("allow_live_coaching", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_personal_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_emoji", sa.String(length=8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["audience_newcomer_id"], ["newcomer_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_arena_scenarios_id"), "arena_scenarios", ["id"], unique=False)
    op.create_index(op.f("ix_arena_scenarios_mentor_id"), "arena_scenarios", ["mentor_id"], unique=False)
    op.create_index(
        op.f("ix_arena_scenarios_audience_newcomer_id"),
        "arena_scenarios",
        ["audience_newcomer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_arena_scenarios_is_personal_bot"),
        "arena_scenarios",
        ["is_personal_bot"],
        unique=False,
    )

    op.create_table(
        "arena_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("newcomer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("radar_scores", sa.JSON(), nullable=True),
        sa.Column("badges_earned", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("debrief", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["arena_scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_arena_sessions_id"), "arena_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_arena_sessions_scenario_id"), "arena_sessions", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_arena_sessions_newcomer_id"), "arena_sessions", ["newcomer_id"], unique=False)
    op.create_index(op.f("ix_arena_sessions_status"), "arena_sessions", ["status"], unique=False)

    op.create_table(
        "arena_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sender", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["arena_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_arena_messages_id"), "arena_messages", ["id"], unique=False)
    op.create_index(op.f("ix_arena_messages_session_id"), "arena_messages", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_arena_messages_session_id"), table_name="arena_messages")
    op.drop_index(op.f("ix_arena_messages_id"), table_name="arena_messages")
    op.drop_table("arena_messages")
    op.drop_index(op.f("ix_arena_sessions_status"), table_name="arena_sessions")
    op.drop_index(op.f("ix_arena_sessions_newcomer_id"), table_name="arena_sessions")
    op.drop_index(op.f("ix_arena_sessions_scenario_id"), table_name="arena_sessions")
    op.drop_index(op.f("ix_arena_sessions_id"), table_name="arena_sessions")
    op.drop_table("arena_sessions")
    op.drop_index(op.f("ix_arena_scenarios_is_personal_bot"), table_name="arena_scenarios")
    op.drop_index(op.f("ix_arena_scenarios_audience_newcomer_id"), table_name="arena_scenarios")
    op.drop_index(op.f("ix_arena_scenarios_mentor_id"), table_name="arena_scenarios")
    op.drop_index(op.f("ix_arena_scenarios_id"), table_name="arena_scenarios")
    op.drop_table("arena_scenarios")
