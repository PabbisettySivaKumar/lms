from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class JobLog(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    job_name: str = Field(..., description="Unique identifier for the job run (e.g., yearly_reset_2026)")
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="SUCCESS or FAILED")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Audit logs or result summary")
    executed_by: Optional[str] = None

    class Config:
        populate_by_name = True
