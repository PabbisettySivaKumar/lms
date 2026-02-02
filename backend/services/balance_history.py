"""
Record balance changes in user_balance_history for audit trail.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from backend.models import UserBalanceHistory
from backend.models.balance import UserLeaveBalance
from backend.models.enums import LeaveTypeEnum, BalanceChangeTypeEnum
from sqlalchemy import select, and_  # type: ignore


async def record_balance_change(
    db: AsyncSession,
    user_id: int,
    leave_type: LeaveTypeEnum,
    previous_balance: float,
    new_balance: float,
    change_type: BalanceChangeTypeEnum,
    reason: Optional[str] = None,
    related_leave_id: Optional[int] = None,
    changed_by: Optional[int] = None,
) -> None:
    """
    Insert a row into user_balance_history. Caller must commit.
    change_amount = new_balance - previous_balance (positive = addition, negative = deduction).
    """
    change_amount = round(new_balance - previous_balance, 2)
    if change_amount == 0:
        return
    record = UserBalanceHistory(
        user_id=user_id,
        leave_type=leave_type,
        previous_balance=previous_balance,
        new_balance=new_balance,
        change_amount=change_amount,
        change_type=change_type,
        reason=reason,
        related_leave_id=related_leave_id,
        changed_by=changed_by,
    )
    db.add(record)
