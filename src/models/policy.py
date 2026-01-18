from pydantic import BaseModel, Field
from typing import Optional

class LeavePolicy(BaseModel):
    year: int = Field(..., description="Year for which the policy is active")
    casual_leave_quota: int = 12
    sick_leave_quota: int = 5
    wfh_quota: int = 2
    is_active: bool = False
    document_url: Optional[str] = None
    
    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True
