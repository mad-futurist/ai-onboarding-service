"""add rag document chunks and ai questions

Revision ID: 46bc02cf05e7
Revises: 67a4ad0267ae
Create Date: 2026-05-12 13:48:03.520577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '46bc02cf05e7'
down_revision: Union[str, Sequence[str], None] = '67a4ad0267ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )

    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "ai_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("newcomer_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="answered"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["newcomer_id"], ["newcomer_profiles.id"]),
    )

    op.create_index("ix_ai_questions_user_id", "ai_questions", ["user_id"])
    op.create_index("ix_ai_questions_newcomer_id", "ai_questions", ["newcomer_id"])

    op.create_table(
        "ai_question_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["ai_questions.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
    )

    op.create_index("ix_ai_question_sources_question_id", "ai_question_sources", ["question_id"])
    op.create_index("ix_ai_question_sources_document_id", "ai_question_sources", ["document_id"])
    op.create_index("ix_ai_question_sources_chunk_id", "ai_question_sources", ["chunk_id"])

def downgrade() -> None:
    op.drop_index("ix_ai_question_sources_chunk_id", table_name="ai_question_sources")
    op.drop_index("ix_ai_question_sources_document_id", table_name="ai_question_sources")
    op.drop_index("ix_ai_question_sources_question_id", table_name="ai_question_sources")
    op.drop_table("ai_question_sources")

    op.drop_index("ix_ai_questions_newcomer_id", table_name="ai_questions")
    op.drop_index("ix_ai_questions_user_id", table_name="ai_questions")
    op.drop_table("ai_questions")

    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")