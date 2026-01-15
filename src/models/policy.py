from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class PolicyBase(BaseModel):
    title: str
    description: Optional[str] = None

class PolicyCreate(PolicyBase):
    pass

class Policy(PolicyBase):
    id: str = Field(..., alias="_id")
    file_url: str
    created_at: datetime
    
    # User specific field (not stored in policies coll, but returned in API)
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

class PolicyAcknowledgment(BaseModel):
    user_id: str
    policy_id: str
    acknowledged_at: datetime
