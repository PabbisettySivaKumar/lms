"""
Policy-related SQLAlchemy models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime
from backend.db import Base
from typing import Optional, List
from pydantic import BaseModel, Field


# Define PolicyDocument before Policy since Policy has a relationship to PolicyDocument
class PolicyDocument(Base):
    """Policy documents table"""
    __tablename__ = "policy_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    policy = relationship("Policy", back_populates="policy_documents")
    
    __table_args__ = (
        Index("idx_policy_id", "policy_id"),
        Index("idx_uploaded_at", "uploaded_at"),
    )


class Policy(Base):
    """Policies table"""
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, unique=True, nullable=False, comment="Year for which policy is active")
    casual_leave_quota = Column(Integer, nullable=False, default=12)
    sick_leave_quota = Column(Integer, nullable=False, default=5)
    wfh_quota = Column(Integer, nullable=False, default=2)
    is_active = Column(Boolean, default=False, comment="Only one policy should be active per year")
    document_url = Column(String(500), nullable=True)  # Deprecated
    document_name = Column(String(255), nullable=True)  # Deprecated
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    
    # Relationships
    policy_documents = relationship("PolicyDocument", back_populates="policy", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_year", "year"),
        Index("idx_is_active", "is_active"),
    )


class PolicyAcknowledgment(Base):
    """Policy acknowledgments table"""
    __tablename__ = "policy_acknowledgments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False, comment="Policy year")
    document_url = Column(String(500), nullable=False, comment="URL of the acknowledged document")
    acknowledged_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    __table_args__ = (
        UniqueConstraint("user_id", "year", "document_url", name="unique_user_document_year"),
        Index("idx_user_id", "user_id"),
        Index("idx_year", "year"),
        Index("idx_user_year", "user_id", "year"),
        Index("idx_year_document", "year", "document_url"),
        Index("idx_acknowledged_at", "acknowledged_at"),
    )



# Pydantic Models (for API request/response)
# Pydantic PolicyDocument model
# Note: SQLAlchemy PolicyDocument model is imported separately
class _PolicyDocumentPydantic(BaseModel):
    """Model for policy document"""
    id: Optional[int] = None
    policy_id: Optional[int] = None
    name: str
    url: str
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Export Pydantic model as PolicyDocumentSchema
# Note: SQLAlchemy PolicyDocument model is kept as PolicyDocument
PolicyDocumentSchema = _PolicyDocumentPydantic


class LeavePolicy(BaseModel):
    """Model for policies table"""
    id: Optional[int] = None
    year: int = Field(..., description="Year for which the policy is active")
    casual_leave_quota: int = 12
    sick_leave_quota: int = 5
    wfh_quota: int = 2
    is_active: bool = False
    
    # Deprecated fields (kept for backward compatibility)
    document_url: Optional[str] = None
    document_name: Optional[str] = None
    
    # Documents are in separate policy_documents table
    documents: List["PolicyDocumentSchema"] = []  # This field is not a DB column
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        from_attributes = True


# Pydantic PolicyAcknowledgment model
# Note: SQLAlchemy PolicyAcknowledgment model is imported separately
class _PolicyAcknowledgmentPydantic(BaseModel):
    """Model for policy acknowledgment"""
    id: Optional[int] = None
    user_id: int
    year: int
    document_url: str
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Export Pydantic model as PolicyAcknowledgmentSchema
# Note: SQLAlchemy PolicyAcknowledgment model is kept as PolicyAcknowledgment
PolicyAcknowledgmentSchema = _PolicyAcknowledgmentPydantic
