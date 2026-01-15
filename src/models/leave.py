from enum import Enum
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

class LeaveType(str, Enum):
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"
    WFH = "WFH"
    COMP_OFF = "COMP_OFF"
    MATERNITY = "MATERNITY"
    SABBATICAL = "SABBATICAL"

class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"

class CompOffStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class HolidayBase(BaseModel):
    name: str
    date: date
    year: int
    is_optional: bool = False

class HolidayCreate(HolidayBase):
    pass

class Holiday(HolidayBase):
    id: Optional[str] = Field(None, alias="_id")

class CompOffClaimBase(BaseModel):
    claimant_id: str
    work_date: date
    reason: str
    status: CompOffStatus = CompOffStatus.PENDING
    approver_id: Optional[str] = None

class CompOffClaimCreate(BaseModel):
    work_date: date
    reason: str

class CompOffClaim(CompOffClaimBase):
    id: Optional[str] = Field(None, alias="_id")

class LeaveRequestBase(BaseModel):
    applicant_id: str
    type: LeaveType
    start_date: date
    end_date: Optional[date] = None
    reason: str
    status: LeaveStatus = LeaveStatus.PENDING
    deductible_days: float = 0.0
    approver_id: Optional[str] = None

class LeaveRequestCreate(BaseModel):
    type: LeaveType
    start_date: date
    end_date: Optional[date] = None
    reason: str

class LeaveRequest(LeaveRequestBase):
    id: Optional[str] = Field(None, alias="_id")
