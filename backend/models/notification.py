"""
Notification SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum, Index, text  # type: ignore
from datetime import datetime
from backend.db import Base
from backend.models.enums import NotificationTypeEnum


class Notification(Base):
    """Notifications table"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    type = Column(SQLEnum(NotificationTypeEnum), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    related_leave_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_is_read", "is_read"),
        Index("idx_user_read", "user_id", "is_read"),
        Index("idx_created_at", "created_at"),
        Index("idx_type", "type"),
    )
