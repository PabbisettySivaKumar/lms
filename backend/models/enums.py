"""
SQLAlchemy Enum definitions
"""
import enum


class LeaveTypeEnum(str, enum.Enum):
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"
    WFH = "WFH"
    COMP_OFF = "COMP_OFF"
    MATERNITY = "MATERNITY"
    SABBATICAL = "SABBATICAL"


class LeaveStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"


class CompOffStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BalanceChangeTypeEnum(str, enum.Enum):
    DEDUCTION = "DEDUCTION"
    REFUND = "REFUND"
    ACCRUAL = "ACCRUAL"
    YEARLY_RESET = "YEARLY_RESET"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    INITIAL = "INITIAL"


class NotificationTypeEnum(str, enum.Enum):
    LEAVE_APPROVED = "LEAVE_APPROVED"
    LEAVE_REJECTED = "LEAVE_REJECTED"
    LEAVE_PENDING = "LEAVE_PENDING"
    BALANCE_LOW = "BALANCE_LOW"
    POLICY_UPDATED = "POLICY_UPDATED"
    SYSTEM = "SYSTEM"


class JobStatusEnum(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
