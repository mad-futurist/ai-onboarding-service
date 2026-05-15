"""add plan period fields

Revision ID: a42c9e1d7b13
Revises: f31d8a2c4b67
Create Date: 2026-05-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a42c9e1d7b13"
down_revision = "f31d8a2c4b67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("onboarding_plans", sa.Column("period_label", sa.String(length=255), nullable=True))
    op.add_column("onboarding_plans", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("onboarding_plans", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column("onboarding_plans", sa.Column("goal", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("onboarding_plans", "goal")
    op.drop_column("onboarding_plans", "period_end")
    op.drop_column("onboarding_plans", "period_start")
    op.drop_column("onboarding_plans", "period_label")
