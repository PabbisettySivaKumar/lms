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

# Columns to add: (name, type, comment)
_COLUMNS = [
    ("actor_email", sa.String(255), "Email of user who performed the action"),
    ("actor_employee_id", sa.String(50), "Employee ID of actor"),
    ("actor_full_name", sa.String(255), "Full name of actor at time of action"),
    ("actor_role", sa.String(50), "Role of actor at time of action"),
    ("summary", sa.Text(), "Human-readable one-line summary"),
    ("request_method", sa.String(10), "e.g. POST, PATCH"),
    ("request_path", sa.String(500), "e.g. /leaves/5/cancel"),
]


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return r is not None


def _index_exists(conn, index: str, table: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :idx"
        ),
        {"t": table, "idx": index},
    ).scalar()
    return r is not None


def upgrade() -> None:
    conn = op.get_bind()
    for name, col_type, comment in _COLUMNS:
        if not _column_exists(conn, "audit_logs", name):
            op.add_column(
                "audit_logs",
                sa.Column(name, col_type, nullable=True, comment=comment),
            )
    if not _index_exists(conn, "idx_actor_email", "audit_logs"):
        op.create_index("idx_actor_email", "audit_logs", ["actor_email"], unique=False)
    if not _index_exists(conn, "idx_created_at_action", "audit_logs"):
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
