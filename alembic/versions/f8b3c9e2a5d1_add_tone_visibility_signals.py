"""add tone to signals, visibility/author_role to feedback, acknowledged_at

Revision ID: f8b3c9e2a5d1
Revises: d4f7a8b3c1e2
Create Date: 2026-05-17 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8b3c9e2a5d1"
down_revision: Union[str, Sequence[str], None] = "d4f7a8b3c1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_signals",
        sa.Column(
            "tone",
            sa.String(length=20),
            nullable=False,
            server_default="attention",
        ),
    )
    op.add_column(
        "ai_signals",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ai_signal_feedbacks",
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="mentor_only",
        ),
    )
    op.add_column(
        "ai_signal_feedbacks",
        sa.Column("author_role", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_signal_feedbacks", "author_role")
    op.drop_column("ai_signal_feedbacks", "visibility")
    op.drop_column("ai_signals", "acknowledged_at")
    op.drop_column("ai_signals", "tone")
