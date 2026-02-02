"""
Models package for Leave Management System
All models match the MySQL schema defined in MYSQL_SCHEMA_FINAL.sql

SQLAlchemy ORM models are split by domain for better organization.
Pydantic models are in the same files as their corresponding SQLAlchemy models.
"""

# Enums
from .enums import (
    LeaveTypeEnum,
    LeaveStatusEnum,
    CompOffStatusEnum,
    BalanceChangeTypeEnum,
    NotificationTypeEnum,
    JobStatusEnum,
)

# SQLAlchemy Models - Import in order to resolve relationships
# Import models that don't have dependencies first
from .enums import *  # Import all enums first
from .role import Role, RoleScope, UserRole as _UserRoleSQLAlchemy
from .holiday import Holiday
from .job import JobLog
from .audit import AuditLog
from .notification import Notification
# Import PolicyDocument before Policy since Policy has a relationship to PolicyDocument
from .policy import PolicyDocument, PolicyAcknowledgment, Policy
from .balance import UserLeaveBalance, UserBalanceHistory
from .leave import LeaveRequestModel, CompOffClaimModel, LeaveComment, LeaveAttachment
# Re-export SQLAlchemy models with original names
LeaveRequest = LeaveRequestModel
CompOffClaim = CompOffClaimModel
# Import User last since it has relationships to many other models
from .user import User as _UserSQLAlchemy, UserDocument
from .user_profile import UserProfile
from .staff_role import StaffRole

# Pydantic Models (from user.py, leave.py, policy.py, etc.)
from .user import (
    UserRole as UserRoleEnum,
    UserBase,
    UserSchema,
    UserInDB,
    UserCreate,
    UserCreateAdmin,
    UserUpdateAdmin,
    UserUpdateProfile,
    UserBalanceUpdate,
)

# Export SQLAlchemy models with their names
User = _UserSQLAlchemy
UserRole = _UserRoleSQLAlchemy
from .leave import (
    LeaveType,
    LeaveStatus,
    CompOffStatus,
    LeaveRequestSchema as LeaveRequestPydantic,
    LeaveRequestBase,
    LeaveRequestCreate,
    CompOffClaimSchema as CompOffClaimPydantic,
    CompOffClaimBase,
    CompOffClaimCreate,
    Holiday as HolidayPydantic,
    HolidayBase,
    HolidayCreate,
)
from .policy import (
    LeavePolicy,
    PolicyDocumentSchema,
    PolicyAcknowledgmentSchema,
)
from .job import JobLogSchema as JobLogPydantic

# Re-export for backward compatibility
__all__ = [
    # Enums
    "LeaveTypeEnum",
    "LeaveStatusEnum",
    "CompOffStatusEnum",
    "BalanceChangeTypeEnum",
    "NotificationTypeEnum",
    "JobStatusEnum",
    # SQLAlchemy Models
    "User",
    "UserDocument",
    "UserProfile",
    "StaffRole",
    "Role",
    "RoleScope",
    "UserRole",
    "UserLeaveBalance",
    "UserBalanceHistory",
    "LeaveRequest",
    "CompOffClaim",
    "LeaveComment",
    "LeaveAttachment",
    "Policy",
    "PolicyDocument",
    "PolicyAcknowledgment",
    "Holiday",
    "Notification",
    "AuditLog",
    "JobLog",
    # Pydantic Models
    "UserRoleEnum",
    "UserBase",
    "UserSchema",
    "UserInDB",
    "UserCreate",
    "UserCreateAdmin",
    "UserUpdateAdmin",
    "UserUpdateProfile",
    "UserBalanceUpdate",
    # Leave Pydantic Models
    "LeaveType",
    "LeaveStatus",
    "CompOffStatus",
    "LeaveRequestPydantic",
    "LeaveRequestBase",
    "LeaveRequestCreate",
    "CompOffClaimPydantic",
    "CompOffClaimBase",
    "CompOffClaimCreate",
    "HolidayPydantic",
    "HolidayBase",
    "HolidayCreate",
    # Policy Pydantic Models
    "LeavePolicy",
    "PolicyDocumentSchema",
    "PolicyAcknowledgmentSchema",
    # Job Pydantic Models
    "JobLogPydantic",
]
