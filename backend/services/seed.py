"""
Shared seed logic for roles and admin user.
Used by the POST /admin/bootstrap API endpoint.
"""
from datetime import date
from typing import Tuple

from sqlalchemy import select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from backend.models import (
    User as UserModel,
    Role,
    RoleScope,
    UserRole,
    UserLeaveBalance,
    LeaveTypeEnum,
    StaffRole,
)
from backend.models.user import UserRole as UserRoleEnum
from backend.utils.scopes import ROLE_SCOPES
from backend.utils.security import get_password_hash


# Default admin credentials
ADMIN_EMAIL = "admin@dotkonnekt.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_EMPLOYEE_ID = "ADMIN001"
ADMIN_FULL_NAME = "Super Admin"


async def run_seed_roles(db: AsyncSession) -> Tuple[int, int]:
    """
    Seed default roles and role-scope mappings. Does not commit.
    Returns (roles_created, scopes_added).
    """
    result = await db.execute(select(Role))
    existing_roles = result.scalars().all()
    roles_map = {}
    roles_created = 0

    if existing_roles:
        for role in existing_roles:
            roles_map[role.name] = role
    # Add any enum role that is missing from the DB (e.g. co_founder added later)
    for role_enum in UserRoleEnum:
        if role_enum.value not in roles_map:
            role = Role(
                name=role_enum.value,
                display_name=role_enum.value.replace("_", " ").title(),
                description=f"{role_enum.value.replace('_', ' ').title()} role",
                is_active=True,
            )
            db.add(role)
            roles_map[role_enum.value] = role
            roles_created += 1
    if not existing_roles or roles_created > 0:
        await db.flush()

    result = await db.execute(select(RoleScope))
    existing_scopes = result.scalars().all()
    existing_scope_set = {(rs.role_id, rs.scope_name) for rs in existing_scopes}
    scopes_added = 0

    for role_key, scopes in ROLE_SCOPES.items():
        role_name = role_key.value if hasattr(role_key, "value") else role_key
        if role_name not in roles_map:
            continue
        role = roles_map[role_name]
        for scope in scopes:
            if (role.id, scope) not in existing_scope_set:
                db.add(RoleScope(role_id=role.id, scope_name=scope))
                scopes_added += 1

    return (roles_created, scopes_added)


async def run_seed_admin(db: AsyncSession) -> bool:
    """
    Create default admin user if not present. Does not commit.
    Returns True if admin was created, False if already existed.
    """
    result = await db.execute(select(UserModel).where(UserModel.email == ADMIN_EMAIL))
    if result.scalar_one_or_none():
        return False

    admin_user = UserModel(
        employee_id=ADMIN_EMPLOYEE_ID,
        email=ADMIN_EMAIL,
        full_name=ADMIN_FULL_NAME,
        hashed_password=get_password_hash(ADMIN_PASSWORD),
        is_active=True,
        reset_required=False,
        joining_date=date.today(),
        manager_id=None,
    )
    db.add(admin_user)
    await db.flush()
    user_id = admin_user.id

    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if not admin_role:
        admin_role = Role(
            name="admin",
            display_name="Administrator",
            description="Full system access",
            is_active=True,
        )
        db.add(admin_role)
        await db.flush()

    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == admin_role.id,
            UserRole.is_active == True,
        )
    )
    if result.scalar_one_or_none():
        pass  # already assigned
    else:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=admin_role.id,
                is_active=True,
                assigned_by=None,
            )
        )

    # Sync staff_roles for admin
    db.add(StaffRole(user_id=user_id, role_type="admin", is_active=True))

    balances = [
        (LeaveTypeEnum.CASUAL, 12.0),
        (LeaveTypeEnum.SICK, 3.0),
        (LeaveTypeEnum.EARNED, 0.0),
        (LeaveTypeEnum.WFH, 2.0),
        (LeaveTypeEnum.COMP_OFF, 0.0),
    ]
    for leave_type, balance_value in balances:
        result = await db.execute(
            select(UserLeaveBalance).where(
                UserLeaveBalance.user_id == user_id,
                UserLeaveBalance.leave_type == leave_type,
            )
        )
        if not result.scalar_one_or_none():
            db.add(
                UserLeaveBalance(
                    user_id=user_id,
                    leave_type=leave_type,
                    balance=balance_value,
                )
            )

    return True
