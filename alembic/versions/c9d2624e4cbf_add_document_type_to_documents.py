"""add document type to documents

Revision ID: c9d2624e4cbf
Revises: 46bc02cf05e7
Create Date: 2026-05-12 14:31:59.109297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d2624e4cbf'
down_revision: Union[str, Sequence[str], None] = '46bc02cf05e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("document_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "document_type")