"""
Staff roles table - one table for all non-employee roles (founder, co_founder, hr, manager).
One row per (user, role_type); same user can have multiple rows (e.g. hr + manager).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, text  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime
from backend.db import Base


class StaffRole(Base):
    """Staff roles table - non-employee roles: founder, co_founder, hr, manager."""
    __tablename__ = "staff_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        comment="User who has this staff role",
    )
    role_type = Column(String(50), nullable=False, comment="founder, co_founder, hr, manager")
    department = Column(String(255), nullable=True, comment="Optional; e.g. for manager/hr")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="staff_roles", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "role_type", name="uq_staff_role_user_role"),
        Index("idx_staff_role_user_id", "user_id"),
        Index("idx_staff_role_role_type", "role_type"),
        Index("idx_staff_role_is_active", "is_active"),
    )
