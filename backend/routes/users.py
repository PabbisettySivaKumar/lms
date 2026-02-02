from fastapi import APIRouter, HTTPException, Depends, status, Security, Request
from typing import List, Optional
from datetime import datetime
from backend.db import get_db, AsyncSessionLocal, ensure_database_exists, init_db
from backend.models import User as UserModel, UserRole as UserRoleModel, Role, UserLeaveBalance, UserDocument, Policy, LeaveTypeEnum, UserSchema, StaffRole
from backend.models.user import UserCreateAdmin, UserRole
from backend.models.enums import BalanceChangeTypeEnum
from backend.services.balance_history import record_balance_change
from backend.utils.security import get_password_hash
from backend.routes.auth import get_current_user_email, get_optional_user_email, verify_admin, create_scope_dependency
from backend.utils.scopes import Scope
from backend.utils.id_utils import to_int_id
from backend.services.audit import log_action as audit_log_action
from backend.services.seed import run_seed_roles, run_seed_admin, ADMIN_EMAIL, ADMIN_EMPLOYEE_ID
from backend.utils.action_log import log_user_action
from fastapi import UploadFile, File
from sqlalchemy import select, func, and_, or_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from sqlalchemy.orm import selectinload  # type: ignore
import shutil
from pathlib import Path
import os
import json
from sqlalchemy import desc  # type: ignore
from backend.utils.id_utils import to_int_id
from backend.models.user import UserBalanceUpdate

router = APIRouter(prefix="", tags=["Users"])

async def user_model_to_pydantic(user: UserModel, db: AsyncSession) -> UserSchema:
    """Convert SQLAlchemy UserModel to Pydantic User model"""
    # Fetch user's active role
    role_name = ""
    user_role_result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True)
        .limit(1)
    )
    user_role_record = user_role_result.first()
    if user_role_record:
        role_name = user_role_record[1].name.lower()  # Get role name and convert to lowercase
    
    # Fetch user's leave balances from user_leave_balances table
    balance_result = await db.execute(
        select(UserLeaveBalance).where(UserLeaveBalance.user_id == user.id)
    )
    balances = balance_result.scalars().all()
    
    # Initialize balance values (default to 0.0)
    casual_balance = 0.0
    earned_balance = 0.0
    sick_balance = 0.0
    comp_off_balance = 0.0
    wfh_balance = 0.0
    
    # Map balances by leave type
    for balance in balances:
        balance_value = float(balance.balance) if balance.balance else 0.0
        if balance.leave_type == LeaveTypeEnum.CASUAL:
            casual_balance = balance_value
        elif balance.leave_type == LeaveTypeEnum.EARNED:
            earned_balance = balance_value
        elif balance.leave_type == LeaveTypeEnum.SICK:
            sick_balance = balance_value
        elif balance.leave_type == LeaveTypeEnum.COMP_OFF:
            comp_off_balance = balance_value
        elif balance.leave_type == LeaveTypeEnum.WFH:
            wfh_balance = balance_value
    
    # Fetch manager information if manager_id exists
    manager_name = None
    if user.manager_id:
        manager_result = await db.execute(select(UserModel).where(UserModel.id == user.manager_id))
        manager = manager_result.scalar_one_or_none()
        if manager:
            manager_name = manager.full_name
    
    # Fetch user documents
    
    documents_result = await db.execute(
        select(UserDocument).where(UserDocument.user_id == user.id).order_by(desc(UserDocument.uploaded_at))
    )
    documents_list = documents_result.scalars().all()
    documents = []
    for doc in documents_list:
        # Extract saved_filename from URL (last part after /)
        saved_filename = doc.url.split("/")[-1] if doc.url else None
        documents.append({
            "name": doc.name,
            "url": doc.url,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "saved_filename": saved_filename
        })
    
    # Note: hashed_password is required by UserBase but we exclude it from responses
    # We'll set it to empty string for security (it won't be serialized in responses)
    return UserSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        employee_id=user.employee_id,
        role=role_name,  # Include role
        hashed_password="",  # Excluded from responses via response_model_exclude
        is_active=user.is_active,
        reset_required=user.reset_required,
        manager_id=user.manager_id,
        joining_date=user.joining_date,
        employee_type=user.employee_type,
        profile_picture_url=user.profile.profile_picture_url if user.profile else None,
        dob=user.profile.dob if user.profile else None,
        blood_group=user.profile.blood_group if user.profile else None,
        address=user.profile.address if user.profile else None,
        permanent_address=user.profile.permanent_address if user.profile else None,
        father_name=user.profile.father_name if user.profile else None,
        father_dob=user.profile.father_dob if user.profile else None,
        mother_name=user.profile.mother_name if user.profile else None,
        mother_dob=user.profile.mother_dob if user.profile else None,
        spouse_name=user.profile.spouse_name if user.profile else None,
        spouse_dob=user.profile.spouse_dob if user.profile else None,
        children_names=user.profile.children_names if user.profile else None,
        emergency_contact_name=user.profile.emergency_contact_name if user.profile else None,
        emergency_contact_phone=user.profile.emergency_contact_phone if user.profile else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
        casual_balance=casual_balance,
        earned_balance=earned_balance,
        sick_balance=sick_balance,
        comp_off_balance=comp_off_balance,
        wfh_balance=wfh_balance,
        manager_name=manager_name,  # Include manager name
        documents=documents if documents else None,  # Include documents
    )

async def get_current_user(email: str = Depends(get_current_user_email), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserModel).where(UserModel.email == email).options(selectinload(UserModel.profile))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await user_model_to_pydantic(user, db)



@router.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: UserSchema = Depends(get_current_user)):
    return current_user

from backend.models.user import UserUpdateProfile

@router.patch("/users/me", response_model=UserSchema)
async def update_user_me(
    request: Request,
    profile_data: UserUpdateProfile,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            select(UserModel).where(UserModel.id == current_user.id).options(selectinload(UserModel.profile))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use model_dump for Pydantic v2, fallback to dict for v1
        try:
            update_data = profile_data.model_dump(exclude_unset=True)
        except AttributeError:
            # Fallback for Pydantic v1
            update_data = profile_data.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Profile fields live in user_profiles; full_name lives in users
        from backend.models import UserProfile
        profile_fields = {"dob", "blood_group", "address", "permanent_address", "father_name", "father_dob", "mother_name", "mother_dob", "spouse_name", "spouse_dob", "children_names", "emergency_contact_name", "emergency_contact_phone"}
        user_fields = {"full_name"}
        # Capture old values before update (for audit)
        old_values = {}
        for key in update_data.keys():
            if key in user_fields and hasattr(user, key):
                val = getattr(user, key)
                old_values[key] = val.isoformat() if hasattr(val, "isoformat") else val
            if key in profile_fields:
                prof = user.profile
                if prof and hasattr(prof, key):
                    val = getattr(prof, key)
                    old_values[key] = val.isoformat() if hasattr(val, "isoformat") else val
        # Get or create profile for profile updates
        if any(k in profile_fields for k in update_data):
            if not user.profile:
                user.profile = UserProfile(user_id=user.id)
                db.add(user.profile)
        # Update user fields (users table)
        for key in user_fields:
            if key in update_data and hasattr(user, key):
                setattr(user, key, update_data[key])
        # Update profile fields (user_profiles table)
        for key in profile_fields:
            if key in update_data and user.profile and hasattr(user.profile, key):
                setattr(user.profile, key, update_data[key])

        await audit_log_action(
            db,
            "UPDATE_PROFILE",
            "USER",
            user_id=current_user.id,
            affected_entity_id=user.id,
            old_values=old_values,
            new_values=update_data,
            actor_email=current_user.email,
            actor_employee_id=current_user.employee_id,
            actor_full_name=current_user.full_name,
            actor_role=getattr(current_user, "role", None),
            summary=f"{current_user.full_name} updated profile ({', '.join(update_data.keys())})",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        await db.refresh(user)
        log_user_action(
            "UPDATE_PROFILE",
            user_id=current_user.id,
            email=current_user.email,
            employee_id=current_user.employee_id,
            full_name=current_user.full_name,
            role=getattr(current_user, "role", None),
            updated_fields=list(update_data.keys()),
        )
        return await user_model_to_pydantic(user, db)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in update_user_me: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update profile: {str(e)}"
        )

@router.post("/users/me/profile-picture", response_model=UserSchema)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")

    # Create uploads directory if not exists
    UPLOAD_DIR = Path("static/uploads/profile_pictures")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    filename = f"{current_user.id}_{int(datetime.now().timestamp())}{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
        
    # Update user profile picture URL
    # Assuming the app mounts /static at /static
    base_url = "/static/uploads/profile_pictures"
    full_url = f"{base_url}/{filename}"
    
    result = await db.execute(
        select(UserModel).where(UserModel.id == current_user.id).options(selectinload(UserModel.profile))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create user profile
    from backend.models import UserProfile
    if not user.profile:
        user.profile = UserProfile(user_id=user.id)
        db.add(user.profile)
    user.profile.profile_picture_url = full_url
    await db.commit()
    await db.refresh(user)
    
    return await user_model_to_pydantic(user, db)

@router.post("/admin/users", response_model=UserSchema)
async def create_user_admin(
    request: Request,
    user_in: UserCreateAdmin,
    # Use scope-based auth (can also use verify_admin for backward compatibility)
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db),
):
    # Check if email exists
    result = await db.execute(select(UserModel).where(UserModel.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check if employee_id exists
    result = await db.execute(select(UserModel).where(UserModel.employee_id == user_in.employee_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Employee ID {user_in.employee_id} already exists")

    manager_id_db = None
    # Handle manager_employee_id - check for None, empty string, or whitespace
    if user_in.manager_employee_id and user_in.manager_employee_id.strip():
        manager_employee_id_clean = user_in.manager_employee_id.strip()
        result = await db.execute(select(UserModel).where(UserModel.employee_id == manager_employee_id_clean))
        manager = result.scalar_one_or_none()
        if not manager:
            # Provide helpful error message with available managers
            available_managers = []
            try:
                manager_role_names = [UserRole.MANAGER.value, UserRole.HR.value, UserRole.FOUNDER.value, UserRole.CO_FOUNDER.value, UserRole.ADMIN.value]
                # Get role IDs
                role_result = await db.execute(select(Role).where(Role.name.in_(manager_role_names)))
                roles = role_result.scalars().all()
                role_ids = [role.id for role in roles]
                
                if role_ids:
                    # Get users with those roles
                    user_role_result = await db.execute(
                        select(UserRoleModel.user_id)
                        .where(and_(UserRoleModel.role_id.in_(role_ids), UserRoleModel.is_active == True))
                        .limit(10)
                    )
                    manager_user_ids = [row[0] for row in user_role_result.fetchall()]
                    
                    # Get users for those user_ids
                    if manager_user_ids:
                        users_result = await db.execute(select(UserModel).where(UserModel.id.in_(manager_user_ids)))
                        for m in users_result.scalars().all():
                            available_managers.append(f"{m.employee_id} ({m.full_name})")
            except Exception:
                # If there's any error getting managers, just skip the list
                pass
            
            error_msg = f"Manager with employee_id '{manager_employee_id_clean}' not found."
            if available_managers:
                error_msg += f" Available managers: {', '.join(available_managers)}"
            else:
                error_msg += " No managers found in the system. You can leave manager_employee_id empty or create a manager first."
            
            raise HTTPException(status_code=400, detail=error_msg)
        manager_id_db = manager.id
        # Debug logging
        print(f"DEBUG: Setting manager_id_db = {manager_id_db} for manager employee_id = {manager_employee_id_clean}")
    
    # Password Handling
    if len(user_in.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    hashed_password = get_password_hash(user_in.password)
    
    # Fetch active policy
    current_year = datetime.now().year
    policy_result = await db.execute(select(Policy).where(Policy.year == current_year))
    policy = policy_result.scalar_one_or_none()
    
    # Defaults
    sick_quota = 3.0
    wfh_quota = 2
    casual_quota = 12.0
    
    if policy:
        sick_quota = float(policy.sick_leave_quota)
        wfh_quota = int(policy.wfh_quota)
        casual_quota = float(policy.casual_leave_quota)

    initial_cl = casual_quota / 12.0

    # Step 1: Create user
    # Debug logging
    print(f"DEBUG: Creating user with manager_id = {manager_id_db}, manager_employee_id from request = {user_in.manager_employee_id}")
    new_user = UserModel(
        employee_id=user_in.employee_id,
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hashed_password,
        is_active=True,
        reset_required=True,
        employee_type=user_in.employee_type,
        manager_id=manager_id_db,
        joining_date=user_in.joining_date
    )
    db.add(new_user)
    await db.flush()  # Flush to get the ID
    user_id = new_user.id
    
    # Step 1b: Create user profile (1:1 with user)
    from backend.models import UserProfile
    profile_kwargs: dict = {"user_id": user_id}
    if getattr(user_in, "dob", None) is not None:
        profile_kwargs["dob"] = user_in.dob
    db.add(UserProfile(**profile_kwargs))
    
    # Step 2: Assign role to user
    # Role is already normalized to UserRole enum by Pydantic validator
    role_name = user_in.role.value if user_in.role else UserRole.EMPLOYEE.value
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{role_name}' not found")
    
    user_role = UserRoleModel(
        user_id=user_id,
        role_id=role.id,
        is_active=True,
        assigned_by=None
    )
    db.add(user_role)
    # Sync staff_roles for non-employee roles (founder, co_founder, hr, manager, admin)
    if role_name in ("founder", "co_founder", "hr", "manager", "admin"):
        db.add(StaffRole(user_id=user_id, role_type=role_name, is_active=True))
    
    # Step 3: Create leave balances
    balances = [
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.CASUAL, balance=initial_cl),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.SICK, balance=sick_quota),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.EARNED, balance=0.0),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.WFH, balance=wfh_quota),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.COMP_OFF, balance=0.0),
    ]
    db.add_all(balances)

    admin_result = await db.execute(select(UserModel).where(UserModel.email == email))
    admin_user = admin_result.scalar_one_or_none()
    # Record initial balance allocation in user_balance_history
    for lt, val in [
        (LeaveTypeEnum.CASUAL, initial_cl),
        (LeaveTypeEnum.SICK, sick_quota),
        (LeaveTypeEnum.EARNED, 0.0),
        (LeaveTypeEnum.WFH, wfh_quota),
        (LeaveTypeEnum.COMP_OFF, 0.0),
    ]:
        if val != 0:
            await record_balance_change(
                db, user_id, lt, 0.0, float(val), BalanceChangeTypeEnum.INITIAL,
                reason="Initial allocation", changed_by=admin_user.id if admin_user else None
            )

    await audit_log_action(
        db,
        "CREATE_USER",
        "USER",
        user_id=admin_user.id if admin_user else None,
        affected_entity_id=new_user.id,
        new_values={"email": new_user.email, "employee_id": new_user.employee_id, "full_name": new_user.full_name},
        actor_email=admin_user.email if admin_user else None,
        actor_employee_id=admin_user.employee_id if admin_user else None,
        actor_full_name=admin_user.full_name if admin_user else None,
        summary=f"{admin_user.full_name if admin_user else 'Admin'} created user {new_user.full_name} ({new_user.employee_id})" if admin_user else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    await db.refresh(new_user)
    if admin_user:
        log_user_action(
            "CREATE_USER",
            user_id=admin_user.id,
            email=admin_user.email,
            employee_id=admin_user.employee_id,
            full_name=admin_user.full_name,
            created_user_id=new_user.id,
            created_email=new_user.email,
            created_employee_id=new_user.employee_id,
        )
    # Refetch with profile loaded (avoid lazy load in user_model_to_pydantic)
    result = await db.execute(
        select(UserModel).where(UserModel.id == new_user.id).options(selectinload(UserModel.profile))
    )
    user_for_response = result.scalar_one_or_none()
    if user_for_response is None:
        await db.refresh(new_user, attribute_names=["profile"])
        user_for_response = new_user
    return await user_model_to_pydantic(user_for_response, db)

@router.get("/admin/managers", response_model=List[dict])
async def list_managers(admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    managers = []
    # Get role IDs for manager, HR, and founder roles
    role_names = [UserRole.MANAGER.value, UserRole.HR.value, UserRole.FOUNDER.value, UserRole.CO_FOUNDER.value]
    role_result = await db.execute(select(Role).where(Role.name.in_(role_names)))
    manager_roles = role_result.scalars().all()
    
    if not manager_roles:
        return managers
    
    role_ids = [role.id for role in manager_roles]
    
    # Find users with these roles
    result = await db.execute(
        select(UserRoleModel, UserModel, Role)
        .join(UserModel, UserRoleModel.user_id == UserModel.id)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(and_(UserRoleModel.role_id.in_(role_ids), UserRoleModel.is_active == True))
    )
    
    for user_role, user, role in result.all():
        managers.append({
            "employee_id": user.employee_id,
            "full_name": user.full_name,
            "role": role.name
        })
    
    return managers

@router.get("/admin/users", response_model=dict)
async def list_users(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    # Accept either read:users or admin:users scope
    email: str = Depends(create_scope_dependency([Scope.READ_USERS, Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db)
):
    """
    List users with pagination and optional search.
    """
    # Build query (eager-load profile to avoid async lazy-load in user_model_to_pydantic)
    query = select(UserModel).options(selectinload(UserModel.profile))
    if search:
        # Case-insensitive search across name, email, employee_id
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                UserModel.full_name.ilike(search_pattern),
                UserModel.email.ilike(search_pattern),
                UserModel.employee_id.ilike(search_pattern)
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Fetch paginated users
    query = query.order_by(UserModel.full_name).offset(skip).limit(limit)
    result = await db.execute(query)
    users_list = result.scalars().all()
    
    # Convert users to Pydantic models (async)
    users = []
    for user in users_list:
        users.append(await user_model_to_pydantic(user, db))
    
    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }



@router.patch("/admin/users/{user_id}/balance", response_model=UserSchema)
async def update_user_balance(
    request: Request,
    user_id: str,
    balance_data: UserBalanceUpdate,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db),
):
    # Convert user_id to integer
    user_id_int = to_int_id(user_id)
    if not user_id_int:
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id_int).options(selectinload(UserModel.profile))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Use model_dump for Pydantic v2, fallback to dict for v1
    if hasattr(balance_data, 'model_dump'):
        update_data = balance_data.model_dump(exclude_unset=True)
    else:
        update_data = balance_data.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No balance fields provided")
    
    # Map balance fields to leave types
    leave_type_map = {
        "casual_balance": LeaveTypeEnum.CASUAL,
        "sick_balance": LeaveTypeEnum.SICK,
        "comp_off_balance": LeaveTypeEnum.COMP_OFF,
        "earned_balance": LeaveTypeEnum.EARNED,
        "wfh_balance": LeaveTypeEnum.WFH,
    }

    # Capture old balances before update (for audit)
    old_values = {}
    for field_name in update_data.keys():
        if field_name in leave_type_map:
            leave_type = leave_type_map[field_name]
            balance_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(UserLeaveBalance.user_id == user_id_int, UserLeaveBalance.leave_type == leave_type)
                )
            )
            bal = balance_result.scalar_one_or_none()
            old_values[field_name] = float(bal.balance) if bal else 0.0

    admin_result = await db.execute(select(UserModel).where(UserModel.email == email))
    admin_user = admin_result.scalar_one_or_none()

    # Update balances in user_leave_balances table
    for field_name, balance_value in update_data.items():
        if field_name in leave_type_map:
            leave_type = leave_type_map[field_name]
            # Find existing balance
            balance_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(UserLeaveBalance.user_id == user_id_int, UserLeaveBalance.leave_type == leave_type)
                )
            )
            balance = balance_result.scalar_one_or_none()
            
            prev = float(balance.balance) if balance else 0.0
            new_val = float(balance_value)
            if balance:
                balance.balance = new_val
            else:
                # Create new balance entry
                new_balance = UserLeaveBalance(
                    user_id=user_id_int,
                    leave_type=leave_type,
                    balance=new_val
                )
                db.add(new_balance)
            await record_balance_change(
                db, user_id_int, leave_type, prev, new_val, BalanceChangeTypeEnum.MANUAL_ADJUSTMENT,
                reason="Admin balance update", changed_by=admin_user.id if admin_user else None
            )

    admin_result = await db.execute(select(UserModel).where(UserModel.email == email))
    admin_user = admin_result.scalar_one_or_none()
    await audit_log_action(
        db,
        "UPDATE_BALANCE",
        "BALANCE",
        user_id=admin_user.id if admin_user else None,
        affected_entity_id=user_id_int,
        old_values=old_values,
        new_values=update_data,
        actor_email=admin_user.email if admin_user else None,
        actor_employee_id=admin_user.employee_id if admin_user else None,
        actor_full_name=admin_user.full_name if admin_user else None,
        summary=f"{admin_user.full_name if admin_user else 'Admin'} updated balance for user_id={user_id_int}" if admin_user else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    await db.refresh(user)
    if admin_user:
        log_user_action(
            "UPDATE_BALANCE",
            user_id=admin_user.id,
            email=admin_user.email,
            employee_id=admin_user.employee_id,
            full_name=admin_user.full_name,
            target_user_id=user_id_int,
            balances=update_data,
        )
    return await user_model_to_pydantic(user, db)

@router.post("/users/me/documents", response_model=UserSchema)
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    
    # Create documents directory
    user_id = to_int_id(current_user.id)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    UPLOAD_DIR = Path(f"static/uploads/documents/{user_id}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        if not file.filename:
            continue  # Skip files without filename
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            continue # Skip invalid files
        
        # Unique filename to prevent overwrite
        timestamp = int(datetime.now().timestamp())
        safe_filename = file.filename.replace(" ", "_") if file.filename else f"file_{timestamp}"
        saved_filename = f"{timestamp}_{safe_filename}"
        file_path = UPLOAD_DIR / saved_filename
        
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
        
        # Insert document record into user_documents table
        new_document = UserDocument(
            user_id=user_id,
            name=file.filename,
            url=f"/static/uploads/documents/{user_id}/{saved_filename}"
        )
        db.add(new_document)
    
    await db.commit()
    
    # Fetch updated user (eager-load profile for user_model_to_pydantic)
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id).options(selectinload(UserModel.profile))
    )
    updated_user = result.scalar_one_or_none()
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await user_model_to_pydantic(updated_user, db)

@router.delete("/users/me/documents/{filename}", response_model=UserSchema)
async def delete_document(
    filename: str, 
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = to_int_id(current_user.id)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Find document by user_id - filename could be either the name or part of the saved filename in URL
    result = await db.execute(
        select(UserDocument).where(
            and_(
                UserDocument.user_id == user_id,
                or_(
                    UserDocument.name == filename,
                    UserDocument.url.contains(filename)
                )
            )
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Extract saved_filename from URL
    url = document.url
    saved_filename = url.split("/")[-1] if url else filename
    
    # Remove from disk
    file_path = Path(f"static/uploads/documents/{user_id}/{saved_filename}")
    if file_path.exists():
        os.remove(file_path)
    
    # Remove from DB
    await db.delete(document)
    await db.commit()
    
    # Fetch updated user (eager-load profile for user_model_to_pydantic)
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id).options(selectinload(UserModel.profile))
    )
    updated_user = result.scalar_one_or_none()
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await user_model_to_pydantic(updated_user, db)

from backend.services.scheduler import monthly_accrual

@router.post("/admin/trigger-accrual")
async def trigger_accrual(
    email: str = Depends(create_scope_dependency([Scope.TRIGGER_JOBS]))
):
    """
    Manually trigger the monthly accrual process (for testing).
    """
    result = await monthly_accrual()
    if result is not None:
        pass  # Function completed successfully
    return {"message": "Monthly accrual triggered successfully"}

@router.delete("/admin/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db),
):
    # Convert user_id to integer
    user_id_int = to_int_id(user_id)
    if not user_id_int:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await db.execute(select(UserModel).where(UserModel.id == user_id_int))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_values = {"email": user.email, "employee_id": user.employee_id, "full_name": user.full_name}
    admin_result = await db.execute(select(UserModel).where(UserModel.email == email))
    admin_user = admin_result.scalar_one_or_none()
    await audit_log_action(
        db,
        "DELETE_USER",
        "USER",
        user_id=admin_user.id if admin_user else None,
        affected_entity_id=user.id,
        old_values=old_values,
        actor_email=admin_user.email if admin_user else None,
        actor_employee_id=admin_user.employee_id if admin_user else None,
        actor_full_name=admin_user.full_name if admin_user else None,
        summary=f"{admin_user.full_name if admin_user else 'Admin'} deleted user {user.full_name} ({user.employee_id})" if admin_user else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.delete(user)
    await db.commit()
    if admin_user:
        log_user_action(
            "DELETE_USER",
            user_id=admin_user.id,
            email=admin_user.email,
            employee_id=admin_user.employee_id,
            full_name=admin_user.full_name,
            deleted_user_id=user.id,
            deleted_email=user.email,
            deleted_employee_id=user.employee_id,
        )
    return {"message": "User deleted successfully"}

from backend.models.user import UserUpdateAdmin

@router.patch("/admin/users/{user_id}", response_model=UserSchema)
async def update_user_details(
    request: Request,
    user_id: str,
    user_data: UserUpdateAdmin,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db),
):
    # Convert user_id to integer
    user_id_clean = user_id.strip() if isinstance(user_id, str) else str(user_id)
    user_id_int = to_int_id(user_id_clean)
    if not user_id_int:
        raise HTTPException(status_code=400, detail=f"Invalid user ID format: '{user_id}' (must be an integer)")

    # Query by id (eager-load profile for user_model_to_pydantic)
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id_int).options(selectinload(UserModel.profile))
    )
    existing_user = result.scalar_one_or_none()
    if not existing_user:
        # Try to find by employee_id as fallback
        result = await db.execute(
            select(UserModel).where(UserModel.employee_id == user_id).options(selectinload(UserModel.profile))
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            user_id_int = existing_user.id
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"User not found with ID: {user_id_int}. Please verify the user exists in the database."
            )

    update_dict = user_data.dict(exclude={"manager_employee_id", "role"}, exclude_unset=True)

    # Handle role update
    if user_data.role is not None:
        role_name = user_data.role.value if isinstance(user_data.role, UserRole) else str(user_data.role).lower()
        role_result = await db.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail=f"Role '{role_name}' not found")
        
        # Get current active role
        current_role_result = await db.execute(
            select(UserRoleModel, Role)
            .join(Role, UserRoleModel.role_id == Role.id)
            .where(and_(UserRoleModel.user_id == user_id_int, UserRoleModel.is_active == True))
        )
        current_role_record = current_role_result.first()
        
        # Check if user already has this role (active or inactive)
        existing_role_result = await db.execute(
            select(UserRoleModel).where(
                and_(UserRoleModel.user_id == user_id_int, UserRoleModel.role_id == role.id)
            )
        )
        existing_role = existing_role_result.scalar_one_or_none()
        
        # If the new role is the same as current active role, skip update
        if current_role_record and current_role_record[0].role_id == role.id:
            # Role is already active, no change needed
            pass
        else:
            # Handle current active role - deactivate or delete
            if current_role_record:
                current_user_role = current_role_record[0]  # UserRoleModel
                current_role_id = current_user_role.role_id
                
                # Check if there's already an inactive role with the same role_id
                inactive_same_role_result = await db.execute(
                    select(UserRoleModel).where(
                        and_(
                            UserRoleModel.user_id == user_id_int,
                            UserRoleModel.role_id == current_role_id,
                            UserRoleModel.is_active == False
                        )
                    )
                )
                inactive_same_role = inactive_same_role_result.scalar_one_or_none()
                
                if inactive_same_role:
                    # If inactive role already exists, delete the active one to avoid duplicate
                    await db.delete(current_user_role)
                else:
                    # Otherwise, just deactivate it
                    current_user_role.is_active = False
            
            # If user already has this role (but inactive), reactivate it
            if existing_role:
                existing_role.is_active = True
            else:
                # Create new active role assignment
                new_user_role = UserRoleModel(
                    user_id=user_id_int,
                    role_id=role.id,
                    is_active=True,
                    assigned_by=None
                )
                db.add(new_user_role)
            # Sync staff_roles: add for founder/hr/manager/admin, deactivate for others
            staff_role_result = await db.execute(
                select(StaffRole).where(StaffRole.user_id == user_id_int)
            )
            for sr in staff_role_result.scalars().all():
                sr.is_active = False
            if role_name in ("founder", "co_founder", "hr", "manager", "admin"):
                existing_sr_result = await db.execute(
                    select(StaffRole).where(
                        and_(StaffRole.user_id == user_id_int, StaffRole.role_type == role_name)
                    )
                )
                existing_sr = existing_sr_result.scalar_one_or_none()
                if existing_sr:
                    existing_sr.is_active = True
                else:
                    db.add(StaffRole(user_id=user_id_int, role_type=role_name, is_active=True))

    # Handle manager linking
    manager_employee_id = user_data.manager_employee_id
    if manager_employee_id:
        manager_employee_id = manager_employee_id.strip() if isinstance(manager_employee_id, str) else manager_employee_id
        if manager_employee_id and manager_employee_id.lower() not in ["string", "null", "none", ""]:
            result = await db.execute(select(UserModel).where(UserModel.employee_id == manager_employee_id))
            manager = result.scalar_one_or_none()
            if not manager:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Manager with employee_id '{manager_employee_id}' not found. Please provide a valid employee_id."
                )
            update_dict["manager_id"] = manager.id
        elif manager_employee_id == "":
            update_dict["manager_id"] = None
    elif manager_employee_id is None:
        # Only set to None if explicitly provided as None (not if field is missing)
        if hasattr(user_data, 'manager_employee_id') and user_data.manager_employee_id is None:
            update_dict["manager_id"] = None

    # Check if employee_id is being updated
    if "employee_id" in update_dict:
        new_employee_id = update_dict["employee_id"]
        if new_employee_id != existing_user.employee_id:
            result = await db.execute(select(UserModel).where(UserModel.employee_id == new_employee_id))
            existing_user_with_employee_id = result.scalar_one_or_none()
            if existing_user_with_employee_id and existing_user_with_employee_id.id != user_id_int:
                raise HTTPException(
                    status_code=400,
                    detail=f"Employee ID '{new_employee_id}' is already assigned to another user. Please choose a different employee_id."
                )
        else:
            del update_dict["employee_id"]
    
    # Check if email is being updated
    if "email" in update_dict:
        new_email = update_dict["email"]
        if new_email != existing_user.email:
            result = await db.execute(select(UserModel).where(UserModel.email == new_email))
            existing_user_with_email = result.scalar_one_or_none()
            if existing_user_with_email and existing_user_with_email.id != user_id_int:
                raise HTTPException(
                    status_code=400,
                    detail=f"Email '{new_email}' is already registered to another user. Please choose a different email."
                )
        else:
            del update_dict["email"]

    if not update_dict:
        return await user_model_to_pydantic(existing_user, db)

    # Profile fields live in user_profiles; the rest are user (users table) fields
    profile_fields = {"dob", "blood_group", "address", "permanent_address", "father_name", "father_dob", "mother_name", "mother_dob", "spouse_name", "spouse_dob", "children_names", "emergency_contact_name", "emergency_contact_phone"}
    profile_update = {k: v for k, v in update_dict.items() if k in profile_fields}
    user_update = {k: v for k, v in update_dict.items() if k not in profile_fields}

    # Capture old values before update (for audit)
    old_values_user = {k: getattr(existing_user, k) for k in user_update.keys() if hasattr(existing_user, k)}
    for k, v in list(old_values_user.items()):
        if hasattr(v, "isoformat"):
            old_values_user[k] = v.isoformat()
    old_values_profile = {}
    if profile_update and existing_user.profile:
        old_values_profile = {k: getattr(existing_user.profile, k) for k in profile_update.keys() if hasattr(existing_user.profile, k)}
        for k, v in list(old_values_profile.items()):
            if hasattr(v, "isoformat"):
                old_values_profile[k] = v.isoformat()

    # Update user fields (users table)
    for key, value in user_update.items():
        if hasattr(existing_user, key):
            setattr(existing_user, key, value)

    # Update profile fields (user_profiles table)
    if profile_update:
        from backend.models import UserProfile
        if not existing_user.profile:
            existing_user.profile = UserProfile(user_id=existing_user.id)
            db.add(existing_user.profile)
        for key, value in profile_update.items():
            if hasattr(existing_user.profile, key):
                setattr(existing_user.profile, key, value)

    admin_result = await db.execute(select(UserModel).where(UserModel.email == email))
    admin_user = admin_result.scalar_one_or_none()
    old_values_merged = {**old_values_user, **old_values_profile}
    await audit_log_action(
        db,
        "UPDATE_USER",
        "USER",
        user_id=admin_user.id if admin_user else None,
        affected_entity_id=existing_user.id,
        old_values=old_values_merged,
        new_values=update_dict,
        actor_email=admin_user.email if admin_user else None,
        actor_employee_id=admin_user.employee_id if admin_user else None,
        actor_full_name=admin_user.full_name if admin_user else None,
        summary=f"{admin_user.full_name if admin_user else 'Admin'} updated user {existing_user.full_name} ({', '.join(update_dict.keys())})" if admin_user else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    await db.refresh(existing_user)
    if admin_user:
        log_user_action(
            "UPDATE_USER",
            user_id=admin_user.id,
            email=admin_user.email,
            employee_id=admin_user.employee_id,
            full_name=admin_user.full_name,
            target_user_id=existing_user.id,
            target_email=existing_user.email,
            updated_fields=list(update_dict.keys()),
        )
    # Refetch with profile loaded (refresh expires attributes; avoid async lazy load)
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id_int).options(selectinload(UserModel.profile))
    )
    user_for_response = result.scalar_one_or_none()
    return await user_model_to_pydantic(user_for_response or existing_user, db)


STAFF_ROLE_NAMES = ("founder", "co_founder", "hr", "manager", "admin")


async def _bootstrap_auth_optional(
    email: Optional[str] = Depends(get_optional_user_email),
    db: AsyncSession = Depends(get_db),
):
    """Allow unauthenticated when ALLOW_BOOTSTRAP_NO_AUTH=true (first-time deploy); else require admin."""
    import os
    allow_no_auth = os.getenv("ALLOW_BOOTSTRAP_NO_AUTH", "").strip().lower() in ("1", "true", "yes")
    if email is None:
        if allow_no_auth:
            return None
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials required")
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role_result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True)
    )
    row = role_result.first()
    if not row:
        raise HTTPException(status_code=403, detail="User has no active role")
    role_name = row[1].name.lower()
    if role_name not in ("admin", "founder", "co_founder", "hr"):
        raise HTTPException(status_code=403, detail="Admin/founder/co-founder/hr access required")
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "employee_id": user.employee_id}


@router.post("/admin/bootstrap", response_model=dict)
async def bootstrap(_auth=Depends(_bootstrap_auth_optional)):
    """
    Full bootstrap: create database if missing, create all tables, then seed roles and admin user.
    Safe to run multiple times (idempotent).
    - When at least one admin exists: requires admin/founder/hr auth.
    - First-time (no admin yet): set ALLOW_BOOTSTRAP_NO_AUTH=true and call without auth once; then unset.
    """
    await ensure_database_exists()
    await init_db()
    async with AsyncSessionLocal() as db:
        roles_created, scopes_added = await run_seed_roles(db)
        admin_created = await run_seed_admin(db)
        await db.commit()
    return {
        "message": "Bootstrap complete",
        "database_created": True,
        "tables_created": True,
        "roles_created": roles_created,
        "scopes_added": scopes_added,
        "admin_created": admin_created,
        "admin_email": ADMIN_EMAIL if admin_created else None,
        "admin_employee_id": ADMIN_EMPLOYEE_ID if admin_created else None,
    }


@router.post("/admin/backfill-staff-roles", response_model=dict)
async def backfill_staff_roles(
    admin=Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    One-time backfill: copy staff roles from user_roles into staff_roles
    for users who have founder, hr, manager, or admin role.
    Safe to run multiple times (idempotent).
    """
    role_result = await db.execute(
        select(Role.id, Role.name).where(Role.name.in_(STAFF_ROLE_NAMES))
    )
    role_ids_by_name = {name: rid for rid, name in role_result.all()}
    if not role_ids_by_name:
        return {"message": "No staff roles (founder/hr/manager/admin) in roles table", "inserted": 0}
    user_roles_result = await db.execute(
        select(UserRoleModel.user_id, Role.name)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(
            and_(
                UserRoleModel.role_id.in_(role_ids_by_name.values()),
                UserRoleModel.is_active == True,
            )
        )
    )
    pairs = [(row.user_id, row.name) for row in user_roles_result.all()]
    inserted = 0
    for user_id, role_name in pairs:
        existing = await db.execute(
            select(StaffRole).where(
                and_(StaffRole.user_id == user_id, StaffRole.role_type == role_name)
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(StaffRole(user_id=user_id, role_type=role_name, is_active=True))
            inserted += 1
        else:
            # Ensure is_active
            existing.scalar_one_or_none().is_active = True
    await db.commit()
    return {"message": f"Backfill complete. Inserted {inserted} staff_role rows.", "inserted": inserted}


@router.get("/admin/integrity-check")
async def check_data_integrity(admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    # Find duplicate emails using SQLAlchemy
    
    # Group by email and count, having count > 1
    duplicate_emails_query = (
        select(UserModel.email, func.count(UserModel.id).label("count"))
        .group_by(UserModel.email)
        .having(func.count(UserModel.id) > 1)
    )
    
    duplicates = []
    result = await db.execute(duplicate_emails_query)
    
    for row in result.all():
        email, count = row.email, row.count
        details = []
        
        # Fetch all users with this email
        users_result = await db.execute(select(UserModel).where(UserModel.email == email))
        for user in users_result.scalars().all():
            details.append({
                "id": str(user.id),
                "name": user.full_name,
                "email": user.email,
                "is_active": user.is_active
            })
        
        duplicates.append({
            "email": email,
            "count": count,
            "accounts": details
        })
        
    return {"status": "issues_found" if duplicates else "healthy", "duplicates": duplicates}
