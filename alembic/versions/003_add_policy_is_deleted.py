"""Add is_deleted to policies for soft delete (keep documents)

Revision ID: 003_policy_is_deleted
Revises: 002_user_profiles_staff
Create Date: Add is_deleted column to policies

"""
from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


revision = "003_policy_is_deleted"
down_revision = "002_user_profiles_staff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policies",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="Soft delete: hide from list but keep policy and documents"),
    )


def downgrade() -> None:
    op.drop_column("policies", "is_deleted")
