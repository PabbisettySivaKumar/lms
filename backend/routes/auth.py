from fastapi import APIRouter, HTTPException, Depends, status, Security, Request
from pydantic import BaseModel
from backend.db import get_db, AsyncSessionLocal
from backend.services.audit import log_action as audit_log_action
from backend.utils.action_log import log_user_action
from backend.models import User as UserModel, UserRole as UserRoleModel, Role
from backend.utils.security import verify_password, create_access_token, get_password_hash, SECRET_KEY, ALGORITHM
from backend.models.user import UserInDB, UserRole
from backend.utils.scopes import get_scopes_for_role, Scope, has_scope
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy import select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Tuple
from backend.services.email import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

from fastapi.security import OAuth2PasswordRequestForm


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    reset_required: bool
    scope: str = ""  # OAuth2 scope string (space-separated)

class PasswordResetRequest(BaseModel):
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class TokenResetRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

async def get_current_user_email(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


def create_scope_dependency(required_scopes: List[str]):
    """
    Create a dependency function that requires specific scopes.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(email: str = Depends(create_scope_dependency([Scope.ADMIN_USERS]))):
            ...
    """
    async def scope_checker(token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str | None = payload.get("sub")
            scopes: List[str] = payload.get("scopes", [])  # type: ignore
            
            if email is None:
                raise credentials_exception
            
            # Check if token has required scopes (any of them)
            if required_scopes and not any(scope in scopes for scope in required_scopes):
                missing_scopes = [s for s in required_scopes if s not in scopes]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scopes: {', '.join(required_scopes)}",
                    headers={"WWW-Authenticate": f'Bearer scope="{" ".join(required_scopes)}"'},
                )
            
            return email
        except JWTError:
            raise credentials_exception
    
    return scope_checker


async def verify_admin(email: str = Depends(get_current_user_email), db: AsyncSession = Depends(get_db)):
    """Verify user has admin/HR/founder role (backward compatibility)."""
    # Get user by email
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's active role
    result = await db.execute(
        select(UserRoleModel, Role)
        .join(Role, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True)
    )
    user_role_record = result.first()
    
    if not user_role_record:
        raise HTTPException(status_code=403, detail="User has no active role assigned")
    
    # When selecting multiple models, result.first() returns a tuple
    role_name = user_role_record[1].name  # user_role_record[0] is UserRoleModel, [1] is Role
    allowed_roles = [UserRole.ADMIN.value, UserRole.FOUNDER.value, UserRole.HR.value]
    if role_name.lower() not in allowed_roles:
        raise HTTPException(status_code=403, detail="Admin/HR access required")
    
    # Return user dict for backward compatibility
    return {
        "id": user.id,
        "_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "employee_id": user.employee_id,
        "is_active": user.is_active,
        "reset_required": user.reset_required,
        "hashed_password": user.hashed_password,
        "manager_id": user.manager_id,
    }

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Get user by email
        result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        # Check if active
        if not user.is_active:
            raise HTTPException(status_code=400, detail="User is inactive")

        # Get user's active role
        result = await db.execute(
            select(UserRoleModel, Role)
            .join(Role, UserRoleModel.role_id == Role.id)
            .where(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True)
        )
        user_role_record = result.first()
        
        if not user_role_record:
            raise HTTPException(status_code=403, detail="User has no active role assigned")
        
        # When selecting multiple models, result.first() returns a tuple
        role_name = user_role_record[1].name  # user_role_record[0] is UserRoleModel, [1] is Role
        try:
            user_role = UserRole(role_name.lower())  # Convert to lowercase to match enum values
        except ValueError:
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid role '{role_name}' assigned to user. Please contact administrator."
            )
        default_scopes = get_scopes_for_role(user_role)
        
        # If scope requested in login, filter to requested scopes (but only grant what role allows)
        # OAuth2PasswordRequestForm may have 'scope' (string) or 'scopes' (list) depending on FastAPI version
        granted_scopes = default_scopes
        requested_scopes = []
        
        # Try to get scope/scopes from form_data
        if hasattr(form_data, 'scope') and getattr(form_data, 'scope', None):
            # scope is a string (space-separated)
            requested_scopes = getattr(form_data, 'scope', '').split()  # type: ignore
        elif hasattr(form_data, 'scopes') and getattr(form_data, 'scopes', None):
            # scopes is a list
            requested_scopes = getattr(form_data, 'scopes', [])  # type: ignore
        
        if requested_scopes:
            # Only grant scopes that user's role allows
            granted_scopes = [s for s in default_scopes if s in requested_scopes]
        
        # Create token with both role (for backward compatibility) and scopes
        token_data = {
            "sub": user.email,
            "role": role_name,  # Keep for backward compatibility
            "scopes": granted_scopes  # Add OAuth2 scopes
        }
        access_token = create_access_token(data=token_data)

        await audit_log_action(
            db,
            "LOGIN",
            "USER",
            user_id=user.id,
            affected_entity_id=user.id,
            actor_email=user.email,
            actor_employee_id=user.employee_id,
            actor_full_name=user.full_name,
            actor_role=role_name,
            summary=f"{user.full_name} ({role_name}) logged in",
            request_method=request.method,
            request_path=request.url.path,
        )
        log_user_action(
            "LOGIN",
            user_id=user.id,
            email=user.email,
            employee_id=user.employee_id,
            full_name=user.full_name,
            role=role_name,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "reset_required": user.reset_required,
            "scope": " ".join(granted_scopes)  # OAuth2 standard: space-separated scopes
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Login error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.patch("/first-login-reset")
async def first_login_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    email: str = Depends(get_current_user_email),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.reset_required:
         raise HTTPException(status_code=400, detail="Password reset not required for this user")

    hashed_password = get_password_hash(reset_data.new_password)
    user.hashed_password = hashed_password
    user.reset_required = False
    await audit_log_action(
        db,
        "FIRST_LOGIN_RESET",
        "USER",
        user_id=user.id,
        affected_entity_id=user.id,
        actor_email=user.email,
        actor_employee_id=user.employee_id,
        actor_full_name=user.full_name,
        summary=f"{user.full_name} completed first-login password reset",
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    log_user_action("FIRST_LOGIN_RESET", user_id=user.id, email=user.email, employee_id=user.employee_id, full_name=user.full_name)
    return {"message": "Password updated successfully"}

@router.post("/forgot-password")
async def forgot_password(
    request_body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.email == request_body.email))
    user = result.scalar_one_or_none()
    if not user:
        # Return 200 to prevent email enumeration
        return {"message": "If the email exists, a reset link has been sent."}
    
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=15)
    
    user.password_reset_token = token
    user.password_reset_expiry = expiry
    await audit_log_action(
        db,
        "FORGOT_PASSWORD_REQUEST",
        "USER",
        user_id=user.id,
        affected_entity_id=user.id,
        new_values={"email": request_body.email},
    )
    await db.commit()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    # Send Email
    await send_email(
        to_email=request_body.email,
        subject="Reset Password",
        body=f"Target: {request_body.email}\nYour reset token is: {token}\n\nClick here to reset your password:\n{reset_link}\n\nExpires in 15 minutes."
    )
    
    return {"message": "If the email exists, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password_token(
    request_body: TokenResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Find user with matching token and non-expired expiry
    result = await db.execute(
        select(UserModel).where(
            UserModel.password_reset_token == request_body.token,
            UserModel.password_reset_expiry > datetime.utcnow()
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    hashed_password = get_password_hash(request_body.new_password)
    user.hashed_password = hashed_password
    user.reset_required = False
    user.password_reset_token = None
    user.password_reset_expiry = None
    await audit_log_action(
        db,
        "RESET_PASSWORD_TOKEN",
        "USER",
        user_id=user.id,
        affected_entity_id=user.id,
    )
    await db.commit()
    
    return {"message": "Password updated successfully."}

@router.post("/change-password")
async def change_password(
    request_body: ChangePasswordRequest,
    request: Request,
    email: str = Depends(get_current_user_email),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Verify current password
    if not verify_password(request_body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    hashed_password = get_password_hash(request_body.new_password)
    user.hashed_password = hashed_password
    await audit_log_action(
        db,
        "CHANGE_PASSWORD",
        "USER",
        user_id=user.id,
        affected_entity_id=user.id,
        actor_email=user.email,
        actor_employee_id=user.employee_id,
        actor_full_name=user.full_name,
        summary=f"{user.full_name} changed password",
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    log_user_action("CHANGE_PASSWORD", user_id=user.id, email=user.email, employee_id=user.employee_id, full_name=user.full_name)
    return {"message": "Password updated successfully"}
