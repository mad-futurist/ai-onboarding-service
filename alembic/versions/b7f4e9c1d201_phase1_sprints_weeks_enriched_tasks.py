"""phase1 sprints weeks enriched tasks

Revision ID: b7f4e9c1d201
Revises: a0e558e8bb3b
Create Date: 2026-05-14 09:00:00.000000

Phase 1 of the onboarding service evolution.
Additive-only: introduces Sprint and Week entities, enriches OnboardingTask
with acceptance/examples/links/manually_edited_fields plus parallel
week_id/sprint_id references, adds scope/target FKs to AISignal and
PlanAdjustmentSuggestion, and adds source_type/external_url to Document.

No existing column or row is changed. week_number/day_number remain the
source of truth on tasks until a future backfill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f4e9c1d201"
down_revision: Union[str, Sequence[str], None] = "a0e558e8bb3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_day", sa.Integer(), nullable=True),
        sa.Column("end_day", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["onboarding_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sprints_id"), "sprints", ["id"], unique=False)
    op.create_index(op.f("ix_sprints_plan_id"), "sprints", ["plan_id"], unique=False)
    op.create_index("ix_sprints_plan_id_index", "sprints", ["plan_id", "index"], unique=False)

    op.create_table(
        "weeks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("sprint_id", sa.Integer(), nullable=True),
        sa.Column("index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("goals", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["onboarding_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weeks_id"), "weeks", ["id"], unique=False)
    op.create_index(op.f("ix_weeks_plan_id"), "weeks", ["plan_id"], unique=False)
    op.create_index(op.f("ix_weeks_sprint_id"), "weeks", ["sprint_id"], unique=False)
    op.create_index("ix_weeks_plan_id_index", "weeks", ["plan_id", "index"], unique=False)

    # onboarding_tasks: enrichment + parallel FK references
    op.add_column("onboarding_tasks", sa.Column("week_id", sa.Integer(), nullable=True))
    op.add_column("onboarding_tasks", sa.Column("sprint_id", sa.Integer(), nullable=True))
    op.add_column("onboarding_tasks", sa.Column("acceptance_criteria", sa.Text(), nullable=True))
    op.add_column("onboarding_tasks", sa.Column("examples", sa.JSON(), nullable=True))
    op.add_column("onboarding_tasks", sa.Column("links", sa.JSON(), nullable=True))
    op.add_column(
        "onboarding_tasks",
        sa.Column("manually_edited_fields", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_onboarding_tasks_week_id",
        "onboarding_tasks",
        "weeks",
        ["week_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_onboarding_tasks_sprint_id",
        "onboarding_tasks",
        "sprints",
        ["sprint_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_onboarding_tasks_week_id"),
        "onboarding_tasks",
        ["week_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_tasks_sprint_id"),
        "onboarding_tasks",
        ["sprint_id"],
        unique=False,
    )

    # ai_signals: scope + target FKs
    op.add_column("ai_signals", sa.Column("target_scope", sa.String(length=20), nullable=True))
    op.add_column("ai_signals", sa.Column("target_week_id", sa.Integer(), nullable=True))
    op.add_column("ai_signals", sa.Column("target_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_signals_target_week_id",
        "ai_signals",
        "weeks",
        ["target_week_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_signals_target_task_id",
        "ai_signals",
        "onboarding_tasks",
        ["target_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_ai_signals_target_week_id"),
        "ai_signals",
        ["target_week_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_signals_target_task_id"),
        "ai_signals",
        ["target_task_id"],
        unique=False,
    )

    # plan_adjustment_suggestions: same triple
    op.add_column(
        "plan_adjustment_suggestions",
        sa.Column("target_scope", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "plan_adjustment_suggestions",
        sa.Column("target_week_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "plan_adjustment_suggestions",
        sa.Column("target_task_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plan_adjustments_target_week_id",
        "plan_adjustment_suggestions",
        "weeks",
        ["target_week_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_plan_adjustments_target_task_id",
        "plan_adjustment_suggestions",
        "onboarding_tasks",
        ["target_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_plan_adjustment_suggestions_target_week_id"),
        "plan_adjustment_suggestions",
        ["target_week_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plan_adjustment_suggestions_target_task_id"),
        "plan_adjustment_suggestions",
        ["target_task_id"],
        unique=False,
    )

    # documents: source_type + external_url
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("external_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "external_url")
    op.drop_column("documents", "source_type")

    op.drop_index(
        op.f("ix_plan_adjustment_suggestions_target_task_id"),
        table_name="plan_adjustment_suggestions",
    )
    op.drop_index(
        op.f("ix_plan_adjustment_suggestions_target_week_id"),
        table_name="plan_adjustment_suggestions",
    )
    op.drop_constraint(
        "fk_plan_adjustments_target_task_id",
        "plan_adjustment_suggestions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_plan_adjustments_target_week_id",
        "plan_adjustment_suggestions",
        type_="foreignkey",
    )
    op.drop_column("plan_adjustment_suggestions", "target_task_id")
    op.drop_column("plan_adjustment_suggestions", "target_week_id")
    op.drop_column("plan_adjustment_suggestions", "target_scope")

    op.drop_index(op.f("ix_ai_signals_target_task_id"), table_name="ai_signals")
    op.drop_index(op.f("ix_ai_signals_target_week_id"), table_name="ai_signals")
    op.drop_constraint("fk_ai_signals_target_task_id", "ai_signals", type_="foreignkey")
    op.drop_constraint("fk_ai_signals_target_week_id", "ai_signals", type_="foreignkey")
    op.drop_column("ai_signals", "target_task_id")
    op.drop_column("ai_signals", "target_week_id")
    op.drop_column("ai_signals", "target_scope")

    op.drop_index(op.f("ix_onboarding_tasks_sprint_id"), table_name="onboarding_tasks")
    op.drop_index(op.f("ix_onboarding_tasks_week_id"), table_name="onboarding_tasks")
    op.drop_constraint(
        "fk_onboarding_tasks_sprint_id", "onboarding_tasks", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_onboarding_tasks_week_id", "onboarding_tasks", type_="foreignkey"
    )
    op.drop_column("onboarding_tasks", "manually_edited_fields")
    op.drop_column("onboarding_tasks", "links")
    op.drop_column("onboarding_tasks", "examples")
    op.drop_column("onboarding_tasks", "acceptance_criteria")
    op.drop_column("onboarding_tasks", "sprint_id")
    op.drop_column("onboarding_tasks", "week_id")

    op.drop_index("ix_weeks_plan_id_index", table_name="weeks")
    op.drop_index(op.f("ix_weeks_sprint_id"), table_name="weeks")
    op.drop_index(op.f("ix_weeks_plan_id"), table_name="weeks")
    op.drop_index(op.f("ix_weeks_id"), table_name="weeks")
    op.drop_table("weeks")

    op.drop_index("ix_sprints_plan_id_index", table_name="sprints")
    op.drop_index(op.f("ix_sprints_plan_id"), table_name="sprints")
    op.drop_index(op.f("ix_sprints_id"), table_name="sprints")
    op.drop_table("sprints")
