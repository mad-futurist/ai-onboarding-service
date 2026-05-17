"""add task comments and notifications

Revision ID: d8e1f2a4c0b6
Revises: c5a8f3e1d942
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e1f2a4c0b6"
down_revision: Union[str, Sequence[str], None] = "c5a8f3e1d942"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "comment_type",
            sa.String(length=30),
            nullable=False,
            server_default="general",
        ),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["onboarding_tasks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_task_comments_id"), "task_comments", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_task_comments_task_id"),
        "task_comments",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_task_id", sa.Integer(), nullable=True),
        sa.Column("related_comment_id", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_task_id"],
            ["onboarding_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_comment_id"],
            ["task_comments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_id"), "notifications", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_type"),
        "notifications",
        ["type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_related_task_id"),
        "notifications",
        ["related_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_notifications_related_task_id"), table_name="notifications"
    )
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(
        op.f("ix_notifications_user_id"), table_name="notifications"
    )
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")

    op.drop_index(
        op.f("ix_task_comments_task_id"), table_name="task_comments"
    )
    op.drop_index(op.f("ix_task_comments_id"), table_name="task_comments")
    op.drop_table("task_comments")
