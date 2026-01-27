"""
User-related SQLAlchemy models
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey, Index  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime, date
from backend.db import Base
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


class User(Base):
    """Users table"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, nullable=False, comment="Unique Employee ID")
    email = Column(String(255), unique=True, nullable=False, comment="Unique Email Address")
    full_name = Column(String(255), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    reset_required = Column(Boolean, default=True, comment="Password reset required on first login")
    password_reset_token = Column(String(255), nullable=True, comment="Password reset token")
    password_reset_expiry = Column(DateTime, nullable=True, comment="Password reset token expiry")
    
    # Hierarchy
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, comment="Self-referential")
    
    # Employment
    joining_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    employee_type = Column(String(50), default="Full-time")
    
    # Profile
    profile_picture_url = Column(String(500), nullable=True)
    dob = Column(Date, nullable=True)
    blood_group = Column(String(10), nullable=True)
    
    # Addresses
    address = Column(Text, nullable=True, comment="Current address")
    permanent_address = Column(Text, nullable=True, comment="Permanent address")
    
    # Family Details
    father_name = Column(String(255), nullable=True)
    father_dob = Column(Date, nullable=True)
    mother_name = Column(String(255), nullable=True)
    mother_dob = Column(Date, nullable=True)
    spouse_name = Column(String(255), nullable=True)
    spouse_dob = Column(Date, nullable=True)
    children_names = Column(Text, nullable=True, comment="Comma-separated or JSON array")
    
    # Emergency Contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    
    # Relationships
    manager = relationship("User", remote_side=[id], backref="subordinates")
    user_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")
    leave_balances = relationship("UserLeaveBalance", back_populates="user", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequestModel", foreign_keys="LeaveRequestModel.applicant_id", back_populates="applicant")
    
    __table_args__ = (
        Index("idx_email", "email"),
        Index("idx_employee_id", "employee_id"),
        Index("idx_manager_id", "manager_id"),
        Index("idx_is_active", "is_active"),
        Index("idx_created_at", "created_at"),
    )


class UserDocument(Base):
    """User documents table"""
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_uploaded_at", "uploaded_at"),
    )

# Pydantic Models (for API request/response)
class UserRole(str, Enum):
    """User role enum"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    ADMIN = "admin"
    FOUNDER = "founder"
    INTERN = "intern"
    CONTRACT = "contract"


class UserBase(BaseModel):
    """Base user model"""
    employee_id: str
    email: EmailStr
    full_name: str
    is_active: bool = True
    employee_type: str = "Full-time"
    joining_date: Optional[date] = None
    manager_id: Optional[int] = None


class UserCreate(UserBase):
    """Model for user self-registration"""
    password: str


class UserCreateAdmin(BaseModel):
    """Model for admin creating users"""
    employee_id: str
    full_name: str
    email: EmailStr
    joining_date: Optional[date] = None
    manager_employee_id: Optional[str] = Field(None, description="Manager's employee_id (not user ID)")
    password: str
    employee_type: str = "Full-time"
    role: UserRole = UserRole.EMPLOYEE
    
    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v):
        """Convert role to lowercase and validate"""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            # Try to find matching enum value
            for role_enum in UserRole:
                if role_enum.value == v_lower:
                    return role_enum
            # If not found, raise validation error
            raise ValueError(f"Invalid role '{v}'. Must be one of: {', '.join([r.value for r in UserRole])}")
        return v


class UserUpdateAdmin(BaseModel):
    """Model for admin updating users"""
    employee_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    joining_date: Optional[date] = None
    manager_employee_id: Optional[str] = Field(None, description="Manager's employee_id (not user ID)")
    employee_type: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None  # Allow role updates
    dob: Optional[date] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    permanent_address: Optional[str] = None
    father_name: Optional[str] = None
    father_dob: Optional[date] = None
    mother_name: Optional[str] = None
    mother_dob: Optional[date] = None
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    children_names: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v):
        """Convert role to lowercase and validate"""
        if v is None:
            return None
        if isinstance(v, str):
            v_lower = v.lower().strip()
            # Try to find matching enum value
            for role_enum in UserRole:
                if role_enum.value == v_lower:
                    return role_enum
            # If not found, raise validation error
            raise ValueError(f"Invalid role '{v}'. Must be one of: {', '.join([r.value for r in UserRole])}")
        return v


class UserUpdateProfile(BaseModel):
    """Model for user updating their own profile"""
    full_name: Optional[str] = None
    dob: Optional[date] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    permanent_address: Optional[str] = None
    father_name: Optional[str] = None
    father_dob: Optional[date] = None
    mother_name: Optional[str] = None
    mother_dob: Optional[date] = None
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    children_names: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class UserBalanceUpdate(BaseModel):
    """Model for updating user leave balances - accepts multiple balance fields"""
    casual_balance: Optional[float] = Field(None, ge=0, description="Casual leave balance")
    earned_balance: Optional[float] = Field(None, ge=0, description="Earned leave balance")
    sick_balance: Optional[float] = Field(None, ge=0, description="Sick leave balance")
    comp_off_balance: Optional[float] = Field(None, ge=0, description="Comp-off balance")
    wfh_balance: Optional[float] = Field(None, ge=0, description="WFH balance")
    
    class Config:
        # Allow 0 values to be passed (they are valid)
        # The ge=0 constraint will validate that values are >= 0
        pass


class UserInDB(UserBase):
    """User model with database fields"""
    id: int
    hashed_password: str
    reset_required: bool
    profile_picture_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Pydantic User model (exported as UserSchema to avoid overwriting SQLAlchemy User)
class UserSchema(UserBase):
    """User model for API responses"""
    id: int
    role: str = ""  # User's role (fetched from user_roles and roles tables)
    hashed_password: str = ""  # Excluded from responses, set to empty for security
    reset_required: bool = False
    profile_picture_url: Optional[str] = None
    dob: Optional[date] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    permanent_address: Optional[str] = None
    father_name: Optional[str] = None
    father_dob: Optional[date] = None
    mother_name: Optional[str] = None
    mother_dob: Optional[date] = None
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    children_names: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Leave balance fields (optional, defaults to 0)
    casual_balance: float = 0.0
    earned_balance: float = 0.0
    sick_balance: float = 0.0
    comp_off_balance: float = 0.0
    wfh_balance: float = 0.0
    # Manager information (optional, populated from manager_id)
    manager_name: Optional[str] = None
    # Documents (optional, fetched from user_documents table)
    documents: Optional[List[dict]] = None

    class Config:
        from_attributes = True

# Note: SQLAlchemy User model is kept as User
# Pydantic model is exported as UserSchema
# Routes should import User (SQLAlchemy) from backend.models
# Routes should import UserSchema (Pydantic) from backend.models.user for API responses