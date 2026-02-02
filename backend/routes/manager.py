"""
Manager view routes: my team and team presence (who is present on a given day).
Only users with manager/hr/founder/admin role can access.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from typing import List, Optional

from backend.db import get_db
from backend.models import User as UserModel, UserRole as UserRoleModel, Role, LeaveRequest as LeaveRequestModel
from backend.models.enums import LeaveStatusEnum
from backend.models.user import UserRole
from backend.routes.auth import get_current_user_email
from backend.routes.users import user_model_to_pydantic
from sqlalchemy import select, and_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from sqlalchemy.orm import selectinload  # type: ignore

router = APIRouter(prefix="/manager", tags=["Manager view"])


async def verify_manager_or_above(
    email: str = Depends(get_current_user_email),
    db: AsyncSession = Depends(get_db),
):
    """Require current user to have manager, HR, founder, or admin role. Returns User model."""
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True)
    )
    user_role_record = result.first()
    if not user_role_record:
        raise HTTPException(status_code=403, detail="No active role assigned")
    role_name = user_role_record[1].name
    allowed = [UserRole.MANAGER.value, UserRole.HR.value, UserRole.FOUNDER.value, UserRole.CO_FOUNDER.value, UserRole.ADMIN.value]
    if role_name.lower() not in allowed:
        raise HTTPException(status_code=403, detail="Manager or above access required")
    return user


def _team_query(current_user: UserModel, role_name: str):
    """Build team list: HR/admin/founder see all active users; manager sees only direct reports."""
    q = (
        select(UserModel)
        .where(UserModel.is_active == True)
        .order_by(UserModel.full_name)
        .options(selectinload(UserModel.profile))
    )
    if role_name.lower() not in ("hr", "admin", "founder", "co_founder"):
        q = q.where(UserModel.manager_id == current_user.id)
    return q


@router.get("/team", response_model=List[dict])
async def get_my_team(
    manager_user=Depends(verify_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    List team members: HR/admin/founder see all active users; manager sees only direct reports.
    """
    result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == manager_user.id, UserRoleModel.is_active == True)
    )
    role_record = result.first()
    role_name = role_record[1].name if role_record else "manager"
    query = _team_query(manager_user, role_name)
    result = await db.execute(query)
    reports = result.scalars().all()
    out = []
    for u in reports:
        out.append(await user_model_to_pydantic(u, db))
    return [u.model_dump() for u in out]


@router.get("/team/presence", response_model=List[dict])
async def get_team_presence(
    manager_user=Depends(verify_manager_or_above),
    db: AsyncSession = Depends(get_db),
    date_param: Optional[date] = Query(None, alias="date", description="Date (YYYY-MM-DD). Default: today."),
):
    """
    List team members with presence status for the given date.
    HR/admin/founder see all active users; manager sees only direct reports.
    status: "present" = not on approved leave that day; "on_leave" = on approved leave.
    """
    target_date = date_param or date.today()
    result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == manager_user.id, UserRoleModel.is_active == True)
    )
    role_record = result.first()
    role_name = role_record[1].name if role_record else "manager"
    query = _team_query(manager_user, role_name)
    result = await db.execute(query)
    reports = result.scalars().all()
    out = []
    for u in reports:
        row = await user_model_to_pydantic(u, db)
        d = row.model_dump()
        # Check approved leave covering target_date
        leave_result = await db.execute(
            select(LeaveRequestModel).where(
                LeaveRequestModel.applicant_id == u.id,
                LeaveRequestModel.status == LeaveStatusEnum.APPROVED,
                LeaveRequestModel.start_date <= target_date,
                LeaveRequestModel.end_date >= target_date,
            )
        )
        leave = leave_result.scalar_one_or_none()
        if leave:
            d["presence_status"] = "on_leave"
            d["leave_type"] = leave.type.value if hasattr(leave.type, "value") else str(leave.type)
            d["leave_start_date"] = leave.start_date.isoformat() if leave.start_date else None
            d["leave_end_date"] = leave.end_date.isoformat() if leave.end_date else None
        else:
            d["presence_status"] = "present"
            d["leave_type"] = None
            d["leave_start_date"] = None
            d["leave_end_date"] = None
        d["date"] = target_date.isoformat()
        out.append(d)
    return out
