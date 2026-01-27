"""
Audit log SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index  # type: ignore
from datetime import datetime
from backend.db import Base


class AuditLog(Base):
    """Audit logs table"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    action = Column(String(100), nullable=False, comment="e.g., CREATE_USER, APPROVE_LEAVE")
    resource_type = Column(String(50), nullable=False, comment="e.g., USER, LEAVE, BALANCE")
    resource_id = Column(Integer, nullable=True)
    old_values = Column(JSON, nullable=True, comment="Previous values before change")
    new_values = Column(JSON, nullable=True, comment="New values after change")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_action", "action"),
        Index("idx_resource", "resource_type", "resource_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_resource_type", "resource_type"),
    )
