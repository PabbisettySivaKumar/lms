from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PolicyDocument(BaseModel):
    name: str
    url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class LeavePolicy(BaseModel):
    year: int = Field(..., description="Year for which the policy is active")
    casual_leave_quota: int = 12
    sick_leave_quota: int = 5
    wfh_quota: int = 2
    is_active: bool = False
    
    # Deprecated single document fields (kept for backward compatibility if needed, but we prefer list)
    document_url: Optional[str] = None
    document_name: Optional[str] = None
    
    # New multiple documents list
    documents: List[PolicyDocument] = []
    
    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True

class PolicyAcknowledgment(BaseModel):
    user_id: str
    year: int
    document_url: str
    acknowledged_at: datetime = Field(default_factory=datetime.utcnow)
