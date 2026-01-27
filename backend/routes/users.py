from fastapi import APIRouter, HTTPException, Depends, status, Security
from typing import List, Optional
from datetime import datetime
from backend.db import get_db, AsyncSessionLocal
from backend.models import User as UserModel, UserRole as UserRoleModel, Role, UserLeaveBalance, UserDocument, Policy, LeaveTypeEnum, UserSchema
from backend.models.user import UserCreateAdmin, UserRole
from backend.utils.security import get_password_hash
from backend.routes.auth import get_current_user_email, verify_admin, create_scope_dependency
from backend.utils.scopes import Scope
from backend.utils.id_utils import to_int_id
from fastapi import UploadFile, File
from sqlalchemy import select, func, and_, or_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
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
        profile_picture_url=user.profile_picture_url,
        dob=user.dob,
        blood_group=user.blood_group,
        address=user.address,
        permanent_address=user.permanent_address,
        father_name=user.father_name,
        father_dob=user.father_dob,
        mother_name=user.mother_name,
        mother_dob=user.mother_dob,
        spouse_name=user.spouse_name,
        spouse_dob=user.spouse_dob,
        children_names=user.children_names,
        emergency_contact_name=user.emergency_contact_name,
        emergency_contact_phone=user.emergency_contact_phone,
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
    result = await db.execute(select(UserModel).where(UserModel.email == email))
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
    profile_data: UserUpdateProfile,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(UserModel).where(UserModel.id == current_user.id))
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
        
        # Update user fields
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await db.commit()
        await db.refresh(user)
        
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
    
    result = await db.execute(select(UserModel).where(UserModel.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.profile_picture_url = full_url
    await db.commit()
    await db.refresh(user)
    
    return await user_model_to_pydantic(user, db)

@router.post("/admin/users", response_model=UserSchema)
async def create_user_admin(
    user_in: UserCreateAdmin,
    # Use scope-based auth (can also use verify_admin for backward compatibility)
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db)
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
                manager_role_names = [UserRole.MANAGER.value, UserRole.HR.value, UserRole.FOUNDER.value, UserRole.ADMIN.value]
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
    
    # Step 3: Create leave balances
    balances = [
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.CASUAL, balance=initial_cl),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.SICK, balance=sick_quota),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.EARNED, balance=0.0),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.WFH, balance=wfh_quota),
        UserLeaveBalance(user_id=user_id, leave_type=LeaveTypeEnum.COMP_OFF, balance=0.0),
    ]
    db.add_all(balances)
    
    await db.commit()
    await db.refresh(new_user)
    
    return await user_model_to_pydantic(new_user, db)

@router.get("/admin/managers", response_model=List[dict])
async def list_managers(admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    managers = []
    # Get role IDs for manager, HR, and founder roles
    role_names = [UserRole.MANAGER.value, UserRole.HR.value, UserRole.FOUNDER.value]
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
    # Build query
    query = select(UserModel)
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
    user_id: str,
    balance_data: UserBalanceUpdate,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db)
):
    # Convert user_id to integer
    user_id_int = to_int_id(user_id)
    if not user_id_int:
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    result = await db.execute(select(UserModel).where(UserModel.id == user_id_int))
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
            
            if balance:
                balance.balance = float(balance_value)
            else:
                # Create new balance entry
                new_balance = UserLeaveBalance(
                    user_id=user_id_int,
                    leave_type=leave_type,
                    balance=float(balance_value)
                )
                db.add(new_balance)
    
    await db.commit()
    await db.refresh(user)
    
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
    
    # Fetch updated user
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
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
    
    # Fetch updated user
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
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
    user_id: str,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db)
):
    # Convert user_id to integer
    user_id_int = to_int_id(user_id)
    if not user_id_int:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await db.execute(select(UserModel).where(UserModel.id == user_id_int))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
        
    return {"message": "User deleted successfully"}

from backend.models.user import UserUpdateAdmin

@router.patch("/admin/users/{user_id}", response_model=UserSchema)
async def update_user_details(
    user_id: str,
    user_data: UserUpdateAdmin,
    email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS])),
    db: AsyncSession = Depends(get_db)
):
    # Convert user_id to integer
    user_id_clean = user_id.strip() if isinstance(user_id, str) else str(user_id)
    user_id_int = to_int_id(user_id_clean)
    if not user_id_int:
        raise HTTPException(status_code=400, detail=f"Invalid user ID format: '{user_id}' (must be an integer)")

    # Query by id
    result = await db.execute(select(UserModel).where(UserModel.id == user_id_int))
    existing_user = result.scalar_one_or_none()
    if not existing_user:
        # Try to find by employee_id as fallback
        result = await db.execute(select(UserModel).where(UserModel.employee_id == user_id))
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

    # Update user fields
    for key, value in update_dict.items():
        if hasattr(existing_user, key):
            setattr(existing_user, key, value)
    
    await db.commit()
    await db.refresh(existing_user)
    
    return await user_model_to_pydantic(existing_user, db)

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
