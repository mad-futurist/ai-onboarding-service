"""add role target to courses

Revision ID: f31d8a2c4b67
Revises: c8a3e2d5f102
Create Date: 2026-05-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f31d8a2c4b67"
down_revision: Union[str, Sequence[str], None] = "c8a3e2d5f102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("role_target", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_courses_role_target"), "courses", ["role_target"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_courses_role_target"), table_name="courses")
    op.drop_column("courses", "role_target")
