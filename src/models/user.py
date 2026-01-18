from enum import Enum
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, validator

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    FOUNDER = "founder"
    ADMIN = "admin"
    INTERN = "intern"
    CONTRACT = "contract"

class UserBase(BaseModel):
    employee_id: str = Field(..., description="Unique Employee ID")
    email: EmailStr = Field(..., description="Unique Email Address")
    full_name: str
    role: UserRole
    joining_date: Optional[date] = None
    is_active: bool = True
    reset_required: bool = True
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    
    # Leave Balances
    casual_balance: float = 0.0
    sick_balance: float = 0.0
    earned_balance: float = 0.0
    wfh_balance: int = 2
    comp_off_balance: float = 0.0
    profile_picture_url: Optional[str] = None
    documents: List[dict] = [] # List of {"name": str, "url": str, "uploaded_at": str}
    
    # Personal Details
    dob: Optional[date] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    father_dob: Optional[date] = None
    mother_name: Optional[str] = None
    mother_dob: Optional[date] = None
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    children_names: Optional[str] = None
    permanent_address: Optional[str] = None
    
    # Emergency
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Work
    employee_type: str = "Full-time" # Default
    
    # Password Reset
    password_reset_token: Optional[str] = None
    password_reset_expiry: Optional[datetime] = None

    @validator('full_name', check_fields=False)
    def name_must_be_title_case(cls, v):
        return v.title()

class UserBalanceUpdate(BaseModel):
    casual_balance: Optional[float] = None
    sick_balance: Optional[float] = None
    comp_off_balance: Optional[float] = None
    earned_balance: Optional[float] = None
    wfh_balance: Optional[int] = None

class UserUpdateProfile(BaseModel):
    blood_group: Optional[str] = None
    address: Optional[str] = None
    permanent_address: Optional[str] = None
    children_names: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    father_dob: Optional[date] = None
    mother_name: Optional[str] = None
    mother_dob: Optional[date] = None
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    dob: Optional[date] = None

class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    manager_id: Optional[str] = None
    employee_id: Optional[str] = None
    joining_date: Optional[date] = None

class UserCreateAdmin(BaseModel):
    employee_id: str
    full_name: str
    email: EmailStr
    role: UserRole = UserRole.EMPLOYEE
    joining_date: Optional[date] = None
    manager_id: Optional[str] = None
    password: str

    @validator('full_name', check_fields=False)
    def name_must_be_title_case(cls, v):
        return v.title()

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str

class User(UserBase):
    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True
