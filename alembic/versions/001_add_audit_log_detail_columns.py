"""Add detailed columns to audit_logs table

Revision ID: 001_audit_detail
Revises:
Create Date: Add actor_*, summary, request_method, request_path to audit_logs

"""
from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


# revision identifiers, used by Alembic.
revision = "001_audit_detail"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("actor_email", sa.String(255), nullable=True, comment="Email of user who performed the action"))
    op.add_column("audit_logs", sa.Column("actor_employee_id", sa.String(50), nullable=True, comment="Employee ID of actor"))
    op.add_column("audit_logs", sa.Column("actor_full_name", sa.String(255), nullable=True, comment="Full name of actor at time of action"))
    op.add_column("audit_logs", sa.Column("actor_role", sa.String(50), nullable=True, comment="Role of actor at time of action"))
    op.add_column("audit_logs", sa.Column("summary", sa.Text(), nullable=True, comment="Human-readable one-line summary"))
    op.add_column("audit_logs", sa.Column("request_method", sa.String(10), nullable=True, comment="e.g. POST, PATCH"))
    op.add_column("audit_logs", sa.Column("request_path", sa.String(500), nullable=True, comment="e.g. /leaves/5/cancel"))
    op.create_index("idx_actor_email", "audit_logs", ["actor_email"], unique=False)
    op.create_index("idx_created_at_action", "audit_logs", ["created_at", "action"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_created_at_action", table_name="audit_logs")
    op.drop_index("idx_actor_email", table_name="audit_logs")
    op.drop_column("audit_logs", "request_path")
    op.drop_column("audit_logs", "request_method")
    op.drop_column("audit_logs", "summary")
    op.drop_column("audit_logs", "actor_role")
    op.drop_column("audit_logs", "actor_full_name")
    op.drop_column("audit_logs", "actor_employee_id")
    op.drop_column("audit_logs", "actor_email")
