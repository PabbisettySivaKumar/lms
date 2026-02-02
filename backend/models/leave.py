"""
Leave-related SQLAlchemy models
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, DECIMAL, ForeignKey, Enum as SQLEnum, Index, text  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime, date
from backend.db import Base
from backend.models.enums import LeaveTypeEnum, LeaveStatusEnum, CompOffStatusEnum
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class LeaveRequestModel(Base):
    """Leave requests table"""
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    applicant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    type = Column(SQLEnum(LeaveTypeEnum), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True, comment="NULL for open-ended Sabbatical leaves")
    deductible_days = Column(DECIMAL(5, 2), nullable=False, default=0.00)
    status = Column(SQLEnum(LeaveStatusEnum), nullable=False, default="PENDING")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Relationships
    applicant = relationship("User", foreign_keys=[applicant_id], back_populates="leave_requests")
    approver = relationship("User", foreign_keys=[approver_id], overlaps="leave_requests")
    
    __table_args__ = (
        Index("idx_applicant_id", "applicant_id"),
        Index("idx_approver_id", "approver_id"),
        Index("idx_status", "status"),
        Index("idx_type", "type"),
        Index("idx_applicant_status", "applicant_id", "status"),
        Index("idx_dates", "start_date", "end_date"),
        Index("idx_created_at", "created_at"),
        Index("idx_approver_status", "approver_id", "status"),
    )


class CompOffClaimModel(Base):
    """Comp-off claims table"""
    __tablename__ = "comp_off_claims"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    claimant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    work_date = Column(Date, nullable=False, comment="Date on which employee worked")
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(CompOffStatusEnum), nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    approved_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_claimant_id", "claimant_id"),
        Index("idx_approver_id", "approver_id"),
        Index("idx_status", "status"),
        Index("idx_work_date", "work_date"),
        Index("idx_claimant_status", "claimant_id", "status"),
        Index("idx_created_at", "created_at"),
    )


class LeaveComment(Base):
    """Leave comments table"""
    __tablename__ = "leave_comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    leave_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, comment="Internal notes not visible to applicant")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        Index("idx_leave_id", "leave_id"),
        Index("idx_user_id", "user_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_is_internal", "is_internal"),
    )


class LeaveAttachment(Base):
    """Leave attachments table"""
    __tablename__ = "leave_attachments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    leave_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True, comment="File size in bytes")
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        Index("idx_leave_id", "leave_id"),
        Index("idx_uploaded_by", "uploaded_by"),
        Index("idx_uploaded_at", "uploaded_at"),
    )


# Pydantic Models (for API request/response)

class LeaveType(str, Enum):
    """Leave type enum"""
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"
    WFH = "WFH"
    COMP_OFF = "COMP_OFF"
    MATERNITY = "MATERNITY"
    SABBATICAL = "SABBATICAL"


class LeaveStatus(str, Enum):
    """Leave status enum"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"


class CompOffStatus(str, Enum):
    """Comp-off status enum"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveRequestBase(BaseModel):
    """Base leave request model"""
    type: LeaveType
    start_date: date
    end_date: Optional[date] = None
    reason: Optional[str] = None


class LeaveRequestCreate(LeaveRequestBase):
    """Model for creating leave request"""
    pass


class LeaveRequestSchema(LeaveRequestBase):
    """Model for leave request response"""
    id: int
    applicant_id: int
    approver_id: Optional[int] = None
    deductible_days: float
    status: LeaveStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Export SQLAlchemy models with their original names for backward compatibility
# Note: These are re-exported in __init__.py to avoid conflicts


class CompOffClaimBase(BaseModel):
    """Base comp-off claim model"""
    work_date: date
    reason: str


class CompOffClaimCreate(CompOffClaimBase):
    """Model for creating comp-off claim"""
    pass


class CompOffClaimSchema(CompOffClaimBase):
    """Model for comp-off claim response"""
    id: int
    claimant_id: int
    approver_id: Optional[int] = None
    status: CompOffStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Export SQLAlchemy models with their original names for backward compatibility
# Note: These are re-exported in __init__.py to avoid conflicts


class HolidayBase(BaseModel):
    """Base holiday model"""
    name: str
    date: date
    year: int
    is_optional: bool = False


class HolidayCreate(HolidayBase):
    """Model for creating holiday"""
    pass


class Holiday(HolidayBase):
    """Model for holiday response"""
    id: int

    class Config:
        from_attributes = True
