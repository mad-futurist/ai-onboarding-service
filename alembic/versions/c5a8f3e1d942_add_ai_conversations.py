"""add ai conversations table and link to ai_questions

Revision ID: c5a8f3e1d942
Revises: b1c4d2e7a9f3
Create Date: 2026-05-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5a8f3e1d942"
down_revision: Union[str, Sequence[str], None] = "b1c4d2e7a9f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("newcomer_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New conversation"),
        sa.Column("context_type", sa.String(length=20), nullable=True),
        sa.Column("context_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_conversations_id"), "ai_conversations", ["id"], unique=False)
    op.create_index(op.f("ix_ai_conversations_user_id"), "ai_conversations", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_conversations_newcomer_id"), "ai_conversations", ["newcomer_id"], unique=False)
    op.create_index(
        "ix_ai_conversations_context",
        "ai_conversations",
        ["context_type", "context_id"],
        unique=False,
    )

    op.add_column(
        "ai_questions",
        sa.Column("conversation_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_questions_conversation_id",
        "ai_questions",
        "ai_conversations",
        ["conversation_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_ai_questions_conversation_id"),
        "ai_questions",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_questions_conversation_id"), table_name="ai_questions")
    op.drop_constraint("fk_ai_questions_conversation_id", "ai_questions", type_="foreignkey")
    op.drop_column("ai_questions", "conversation_id")

    op.drop_index("ix_ai_conversations_context", table_name="ai_conversations")
    op.drop_index(op.f("ix_ai_conversations_newcomer_id"), table_name="ai_conversations")
    op.drop_index(op.f("ix_ai_conversations_user_id"), table_name="ai_conversations")
    op.drop_index(op.f("ix_ai_conversations_id"), table_name="ai_conversations")
    op.drop_table("ai_conversations")
