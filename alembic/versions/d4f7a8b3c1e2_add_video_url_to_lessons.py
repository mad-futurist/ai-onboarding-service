"""add video_url to lessons

Revision ID: d4f7a8b3c1e2
Revises: a42c9e1d7b13
Create Date: 2026-05-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f7a8b3c1e2"
down_revision: Union[str, Sequence[str], None] = "a42c9e1d7b13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("video_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("lessons", "video_url")
