"""add lesson_notes table and lessons.takeaways column

Revision ID: f9c2d7e4a1b5
Revises: f8b3c9e2a5d1
Create Date: 2026-05-15 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c2d7e4a1b5"
down_revision: Union[str, Sequence[str], None] = "f8b3c9e2a5d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("takeaways", sa.JSON(), nullable=True))

    op.create_table(
        "lesson_notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("newcomer_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["newcomer_id"], ["newcomer_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("newcomer_id", "lesson_id", name="uq_lesson_notes_newcomer_lesson"),
    )
    op.create_index(
        "ix_lesson_notes_newcomer_lesson",
        "lesson_notes",
        ["newcomer_id", "lesson_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_notes_newcomer_lesson", table_name="lesson_notes")
    op.drop_table("lesson_notes")
    op.drop_column("lessons", "takeaways")
