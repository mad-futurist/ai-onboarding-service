"""add signal refs to notifications

Revision ID: e2b7a4c9d6f1
Revises: d8e1f2a4c0b6
Create Date: 2026-05-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2b7a4c9d6f1"
down_revision: Union[str, Sequence[str], None] = "d8e1f2a4c0b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("related_signal_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("related_signal_feedback_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_notifications_related_signal_id_ai_signals",
        "notifications",
        "ai_signals",
        ["related_signal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_notifications_related_signal_feedback_id_ai_signal_feedbacks",
        "notifications",
        "ai_signal_feedbacks",
        ["related_signal_feedback_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_notifications_related_signal_id"),
        "notifications",
        ["related_signal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_notifications_related_signal_id"),
        table_name="notifications",
    )
    op.drop_constraint(
        "fk_notifications_related_signal_feedback_id_ai_signal_feedbacks",
        "notifications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notifications_related_signal_id_ai_signals",
        "notifications",
        type_="foreignkey",
    )
    op.drop_column("notifications", "related_signal_feedback_id")
    op.drop_column("notifications", "related_signal_id")
