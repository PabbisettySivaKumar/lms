"""
Utility functions for leave management operations.
Optimized to reduce code duplication and improve performance.
"""
from datetime import date, timedelta
from typing import Optional, Tuple, Union
from backend.models import (
    User as UserModel, UserRole as UserRoleModel, Role,
    UserLeaveBalance, LeaveRequest, Holiday as HolidayModel,
    LeaveStatusEnum, LeaveTypeEnum
)
from backend.models.leave import LeaveType, LeaveStatus
from backend.models.user import UserRole
from backend.models import UserSchema
from sqlalchemy import select, and_, or_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore


# Balance field mapping for leave types
LEAVE_BALANCE_MAP = {
    LeaveType.COMP_OFF: "comp_off_balance",
    LeaveType.CASUAL: "casual_balance",
    LeaveType.SICK: "sick_balance",
    LeaveType.EARNED: "earned_balance",
}


def get_balance_field(leave_type: LeaveType) -> Optional[str]:
    """Get the balance field name for a leave type."""
    return LEAVE_BALANCE_MAP.get(leave_type)


async def determine_approver(user: UserSchema, db: AsyncSession) -> Tuple[Optional[int], Optional[str]]:
    """
    Determine approver for a leave request.
    Returns: (approver_user_id, approver_email)
    Note: Returns user.id (integer) not employee_id (string) for foreign key compatibility
    """
    approver_user_id = None
    approver_email = None
    
    # Use user's manager if exists
    if user.manager_id:
        result = await db.execute(select(UserModel).where(UserModel.id == user.manager_id))
        manager = result.scalar_one_or_none()
        if manager:
            approver_user_id = manager.id  # Return user.id, not employee_id
            approver_email = manager.email
            if approver_user_id:
                return approver_user_id, approver_email
    
    # Fallback to HR if no manager assigned
    # Get HR role from roles table
    result = await db.execute(select(Role).where(Role.name == UserRole.HR.value))
    hr_role = result.scalar_one_or_none()
    if hr_role:
        # Find a user with HR role
        result = await db.execute(
            select(UserRoleModel, UserModel)
            .join(UserModel, UserRoleModel.user_id == UserModel.id)
            .where(and_(UserRoleModel.role_id == hr_role.id, UserRoleModel.is_active == True))
            .limit(1)
        )
        hr_record = result.first()
        if hr_record:
            hr_user = hr_record.UserModel
            approver_user_id = hr_user.id  # Return user.id, not employee_id
            approver_email = hr_user.email
    
    return approver_user_id, approver_email


async def check_leave_overlap(
    applicant_id: Union[str, int],
    new_start: str,
    new_end: Optional[str],
    db: AsyncSession
) -> None:
    """
    Check if a new leave request overlaps with existing active leaves.
    Raises HTTPException if overlap is found.
    """
    from fastapi import HTTPException
    from backend.utils.id_utils import to_int_id
    
    # Convert string dates to date objects for comparison
    new_start_date = date.fromisoformat(new_start) if isinstance(new_start, str) else new_start
    new_end_date = date.fromisoformat(new_end) if (new_end and isinstance(new_end, str)) else (new_end if new_end else None)
    
    # Convert applicant_id to integer
    applicant_id_int = to_int_id(applicant_id)
    if not applicant_id_int:
        raise HTTPException(status_code=400, detail="Invalid applicant ID")
    
    # Fetch all active leaves for user
    result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.applicant_id == applicant_id_int,
                LeaveRequest.status.in_([LeaveStatusEnum.PENDING, LeaveStatusEnum.APPROVED])  # type: ignore[attr-defined]
            )
        )
    )
    active_leaves = result.scalars().all()
    
    for existing_leave in active_leaves:
        existing_start = existing_leave.start_date
        existing_end_raw = existing_leave.end_date  # Might be None for Sabbatical
        
        # existing_end_raw is already a date object or None from SQLAlchemy
        existing_end = existing_end_raw
        
        # Case 1: Both defined - standard overlap check
        if new_end_date and existing_end:
            if existing_start <= new_end_date and existing_end >= new_start_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Overlaps with existing leave ({existing_start} to {existing_end})"
                )
        
        # Case 2: Existing is Sabbatical (Infinite End)
        elif not existing_end:
            if new_end_date:
                if new_end_date >= existing_start:
                    raise HTTPException(
                        status_code=400,
                        detail="Overlaps with ongoing Sabbatical"
                    )
            else:
                # Both infinite - overlap
                raise HTTPException(
                    status_code=400,
                    detail="Overlaps with ongoing Sabbatical"
                )
        
        # Case 3: New is Sabbatical (Infinite End)
        elif not new_end_date:
            if existing_end >= new_start_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sabbatical overlaps with existing leave ({existing_start} to {existing_end})"
                )


async def calculate_deductible_days_optimized(
    start_date: date,
    end_date: date,
    db: AsyncSession
) -> float:
    """
    Optimized calculation of deductible days.
    Fetches all holidays in range once instead of querying per day.
    """
    # Fetch all holidays in the date range in one query
    result = await db.execute(
        select(HolidayModel).where(
            and_(
                HolidayModel.date >= start_date,
                HolidayModel.date <= end_date
            )
        )
    )
    holidays = result.scalars().all()
    holiday_dates = {h.date for h in holidays}
    
    deductible = 0.0
    current = start_date
    
    while current <= end_date:
        # Skip weekends (Sat=5, Sun=6)
        if current.weekday() in [5, 6]:
            current += timedelta(days=1)
            continue
        
        # Skip holidays
        if current in holiday_dates:
            current += timedelta(days=1)
            continue
        
        deductible += 1.0
        current += timedelta(days=1)
    
    return deductible


async def update_user_balance(
    user_id: Union[str, int],
    leave_type: LeaveType,
    days: float,
    operation: str = "deduct",  # "deduct" or "refund"
    db: AsyncSession = None
) -> None:
    """
    Update user balance for a leave type.
    Optimized to use single update operation.
    """
    from backend.utils.id_utils import to_int_id
    from backend.db import AsyncSessionLocal
    
    balance_field = get_balance_field(leave_type)
    if not balance_field:
        return  # Maternity/Sabbatical don't have balance fields
    
    increment = -days if operation == "deduct" else days
    
    # Convert user_id to integer
    user_id_int = to_int_id(user_id)
    if not user_id_int:
        raise ValueError(f"Invalid user ID: {user_id}")
    
    # Use provided db session or create a new one
    if db is None:
        async with AsyncSessionLocal() as session:
            await _update_balance_internal(session, user_id_int, leave_type, increment)
            await session.commit()
    else:
        await _update_balance_internal(db, user_id_int, leave_type, increment)


async def _update_balance_internal(
    db: AsyncSession,
    user_id_int: int,
    leave_type: LeaveType,
    increment: float
) -> None:
    """Internal helper to update balance"""
    # Special handling for CASUAL: deduct from earned_balance first, then casual_balance
    # For refunds (increment > 0), refund to casual_balance first
    if leave_type == LeaveType.CASUAL:
        is_deduction = increment < 0
        amount = abs(increment)
        
        if is_deduction:
            # Deduct: earned_balance first, then casual_balance
            earned_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(
                        UserLeaveBalance.user_id == user_id_int,
                        UserLeaveBalance.leave_type == LeaveTypeEnum.EARNED
                    )
                )
            )
            earned_balance = earned_result.scalar_one_or_none()
            
            remaining = amount
            
            if earned_balance and float(earned_balance.balance) > 0:
                # Deduct from earned_balance first
                earned_deduction = min(float(earned_balance.balance), remaining)
                earned_balance.balance = float(earned_balance.balance) - earned_deduction
                remaining -= earned_deduction
            
            # Deduct remaining from casual_balance
            if remaining > 0:
                casual_result = await db.execute(
                    select(UserLeaveBalance).where(
                        and_(
                            UserLeaveBalance.user_id == user_id_int,
                            UserLeaveBalance.leave_type == LeaveTypeEnum.CASUAL
                        )
                    )
                )
                casual_balance = casual_result.scalar_one_or_none()
                
                if casual_balance:
                    casual_balance.balance = float(casual_balance.balance) - remaining
                else:
                    # Create new casual balance record if it doesn't exist
                    new_balance_record = UserLeaveBalance(
                        user_id=user_id_int,
                        leave_type=LeaveTypeEnum.CASUAL,
                        balance=-remaining  # Negative because we're deducting
                    )
                    db.add(new_balance_record)
        else:
            # Refund: refund proportionally or to casual_balance (simpler: refund to casual_balance)
            # Since we deducted from earned first, we could refund to earned first, but casual is primary
            # For simplicity, refund to casual_balance (primary balance type)
            casual_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(
                        UserLeaveBalance.user_id == user_id_int,
                        UserLeaveBalance.leave_type == LeaveTypeEnum.CASUAL
                    )
                )
            )
            casual_balance = casual_result.scalar_one_or_none()
            
            if casual_balance:
                casual_balance.balance = float(casual_balance.balance) + amount
            else:
                # Create new casual balance record if it doesn't exist
                new_balance_record = UserLeaveBalance(
                    user_id=user_id_int,
                    leave_type=LeaveTypeEnum.CASUAL,
                    balance=amount
                )
                db.add(new_balance_record)
        return
    
    # For other leave types, use the standard update
    # Convert leave_type to enum
    leave_type_enum = LeaveTypeEnum[leave_type.value]
    
    # Get current balance
    result = await db.execute(
        select(UserLeaveBalance).where(
            and_(
                UserLeaveBalance.user_id == user_id_int,
                UserLeaveBalance.leave_type == leave_type_enum
            )
        )
    )
    balance = result.scalar_one_or_none()
    
    if balance:
        # Update existing balance
        balance.balance = float(balance.balance) + increment
    else:
        # Create new balance record if it doesn't exist
        new_balance = increment if increment > 0 else 0.0
        new_balance_record = UserLeaveBalance(
            user_id=user_id_int,
            leave_type=leave_type_enum,
            balance=new_balance
        )
        db.add(new_balance_record)


async def check_balance_sufficient(
    user: UserSchema,
    leave_type: LeaveType,
    required_days: float,
    db: AsyncSession = None
) -> None:
    """
    Check if user has sufficient balance for a leave type.
    Raises HTTPException if insufficient.
    """
    from fastapi import HTTPException
    from backend.utils.id_utils import to_int_id
    from backend.db import AsyncSessionLocal
    
    balance_field = get_balance_field(leave_type)
    if not balance_field:
        return  # Maternity/Sabbatical don't require balance check
    
    # Get balance from user_leave_balances table
    user_id = to_int_id(user.id)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Use provided db session or create a new one
    if db is None:
        async with AsyncSessionLocal() as session:
            await _check_balance_internal(session, user_id, leave_type, required_days)
    else:
        await _check_balance_internal(db, user_id, leave_type, required_days)


async def _check_balance_internal(
    db: AsyncSession,
    user_id: int,
    leave_type: LeaveType,
    required_days: float
) -> None:
    """Internal helper to check balance"""
    from fastapi import HTTPException
    
    # Special handling for CASUAL: check both casual_balance and earned_balance
    if leave_type == LeaveType.CASUAL:
        # Get both casual and earned balances
        casual_result = await db.execute(
            select(UserLeaveBalance).where(
                and_(
                    UserLeaveBalance.user_id == user_id,
                    UserLeaveBalance.leave_type == LeaveTypeEnum.CASUAL
                )
            )
        )
        earned_result = await db.execute(
            select(UserLeaveBalance).where(
                and_(
                    UserLeaveBalance.user_id == user_id,
                    UserLeaveBalance.leave_type == LeaveTypeEnum.EARNED
                )
            )
        )
        casual_record = casual_result.scalar_one_or_none()
        earned_record = earned_result.scalar_one_or_none()
        
        casual_balance = float(casual_record.balance) if casual_record else 0.0
        earned_balance = float(earned_record.balance) if earned_record else 0.0
        total_balance = casual_balance + earned_balance
        
        if total_balance < required_days:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient Casual/Earned Leave balance. Available: {total_balance} (Casual: {casual_balance}, Earned: {earned_balance}), Required: {required_days}"
            )
        return
    
    # For other leave types, use the standard check
    # Convert leave_type to enum
    leave_type_enum = LeaveTypeEnum[leave_type.value]
    
    result = await db.execute(
        select(UserLeaveBalance).where(
            and_(
                UserLeaveBalance.user_id == user_id,
                UserLeaveBalance.leave_type == leave_type_enum
            )
        )
    )
    balance_record = result.scalar_one_or_none()
    
    current_balance = float(balance_record.balance) if balance_record else 0.0
    
    if current_balance < required_days:
        leave_type_name = leave_type.value.replace("_", "-").title()
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient {leave_type_name} balance. Available: {current_balance}, Required: {required_days}"
        )
