"""
Balance-related SQLAlchemy models
"""
from sqlalchemy import Column, Integer, DECIMAL, Text, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, text  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime
from backend.db import Base
from backend.models.enums import LeaveTypeEnum, BalanceChangeTypeEnum


class UserLeaveBalance(Base):
    """User leave balances table"""
    __tablename__ = "user_leave_balances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    leave_type = Column(SQLEnum(LeaveTypeEnum), nullable=False)
    balance = Column(DECIMAL(5, 2), nullable=False, default=0.00)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    
    # Relationships
    user = relationship("User", back_populates="leave_balances")
    
    __table_args__ = (
        UniqueConstraint("user_id", "leave_type", name="unique_user_leave_type"),
        Index("idx_user_id", "user_id"),
        Index("idx_leave_type", "leave_type"),
    )


class UserBalanceHistory(Base):
    """User balance history table - audit trail"""
    __tablename__ = "user_balance_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    leave_type = Column(SQLEnum(LeaveTypeEnum), nullable=False)
    previous_balance = Column(DECIMAL(5, 2), nullable=False)
    new_balance = Column(DECIMAL(5, 2), nullable=False)
    change_amount = Column(DECIMAL(5, 2), nullable=False, comment="Positive for addition, negative for deduction")
    change_type = Column(SQLEnum(BalanceChangeTypeEnum), nullable=False)
    reason = Column(Text, nullable=True)
    related_leave_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_leave_type", "leave_type"),
        Index("idx_change_type", "change_type"),
        Index("idx_changed_at", "changed_at"),
        Index("idx_user_type", "user_id", "leave_type"),
        Index("idx_related_leave", "related_leave_id"),
    )
