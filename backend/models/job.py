"""
Job log SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, JSON, Index  # type: ignore
from datetime import datetime
from backend.db import Base
from backend.models.enums import JobStatusEnum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class JobLog(Base):
    """Job logs table"""
    __tablename__ = "job_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(255), unique=True, nullable=False, comment="Unique identifier")
    executed_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    status = Column(SQLEnum(JobStatusEnum), nullable=False)
    details = Column(JSON, nullable=True, comment="Audit logs or result summary as JSON")
    executed_by = Column(String(255), nullable=True, comment="User who triggered the job")
    
    __table_args__ = (
        Index("idx_job_name", "job_name"),
        Index("idx_status", "status"),
        Index("idx_executed_at", "executed_at"),
        Index("idx_job_status", "job_name", "status"),
    )

# Pydantic Models (for API request/response)

# Pydantic JobLog model
# Note: SQLAlchemy JobLog model is imported separately
class _JobLogPydantic(BaseModel):
    """Model for job_logs table"""
    id: Optional[int] = None
    job_name: str = Field(..., description="Unique identifier for the job run (e.g., yearly_reset_2026)")
    executed_at: Optional[datetime] = None
    status: str = Field(..., description="SUCCESS or FAILED")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Audit logs or result summary as JSON")
    executed_by: Optional[str] = None

    class Config:
        populate_by_name = True

# Export Pydantic model as JobLogSchema
# Note: SQLAlchemy JobLog model is kept as JobLog
JobLogSchema = _JobLogPydantic
