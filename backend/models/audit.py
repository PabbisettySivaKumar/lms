"""
Audit log SQLAlchemy model.
Stores who did what, to which record, when.
Column order: id, user_id, actor_*, affected_entity_*, action, summary, request_*, old/new_values, created_at.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index  # type: ignore
from datetime import datetime
from backend.db import Base


class AuditLog(Base):
    """
    Audit logs table - detailed trail of user actions for compliance and support.

    affected_entity_type = kind of record that was affected (USER, LEAVE, POLICY, HOLIDAY, COMP_OFF, JOB, BALANCE).
    affected_entity_id   = primary key of that record (e.g. leave_requests.id, users.id).
    """
    __tablename__ = "audit_logs"

    # --- Identity & actor (who performed the action) ---
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    actor_employee_id = Column(String(50), nullable=True, comment="Employee ID of user who performed the action")
    actor_full_name = Column(String(255), nullable=True, comment="Full name of actor at time of action")
    actor_role = Column(String(50), nullable=True, comment="Role of actor at time of action (e.g. employee, admin)")
    actor_email = Column(String(255), nullable=True, comment="Email of actor")

    # --- Affected entity (which record was acted upon) ---
    affected_entity_id = Column(Integer, nullable=True, comment="ID of the affected record (e.g. leave id, user id)")
    affected_entity_type = Column(String(50), nullable=False, comment="Type of affected record: USER, LEAVE, POLICY, HOLIDAY, COMP_OFF, JOB, BALANCE")

    # --- Action & context ---
    action = Column(String(100), nullable=False, comment="e.g. LOGIN, CREATE_LEAVE, APPROVE_LEAVE")
    summary = Column(Text, nullable=True, comment="Human-readable one-line description")
    request_method = Column(String(10), nullable=True, comment="e.g. POST, PATCH")
    request_path = Column(String(500), nullable=True, comment="e.g. /leaves/apply")

    old_values = Column(JSON, nullable=True, comment="Previous values before change")
    new_values = Column(JSON, nullable=True, comment="New values after change")
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_action", "action"),
        Index("idx_affected_entity", "affected_entity_type", "affected_entity_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_affected_entity_type", "affected_entity_type"),
        Index("idx_actor_email", "actor_email"),
        Index("idx_created_at_action", "created_at", "action"),
    )
