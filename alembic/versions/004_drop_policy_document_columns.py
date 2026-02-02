"""Drop document_url and document_name from policies (documents live in policy_documents)

Revision ID: 004_drop_policy_doc_cols
Revises: 003_policy_is_deleted
Create Date: Drop deprecated document columns from policies table

"""
from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


revision = "004_drop_policy_doc_cols"
down_revision = "003_policy_is_deleted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("policies", "document_url")
    op.drop_column("policies", "document_name")


def downgrade() -> None:
    op.add_column("policies", sa.Column("document_url", sa.String(500), nullable=True))
    op.add_column("policies", sa.Column("document_name", sa.String(255), nullable=True))
