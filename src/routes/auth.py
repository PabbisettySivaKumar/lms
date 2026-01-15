from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from src.db import users_collection
from src.utils.security import verify_password, create_access_token, get_password_hash
from src.models.user import UserInDB
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import os
import secrets
from datetime import datetime, timedelta
from src.services.email import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("SECRET_KEY", "your_super_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

from fastapi.security import OAuth2PasswordRequestForm


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    reset_required: bool

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
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_doc = await users_collection.find_one({"email": form_data.username})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Verify password (assuming hashed_password field exists)
    if not verify_password(form_data.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check if active
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="User is inactive")

    access_token = create_access_token(data={"sub": user_doc["email"], "role": user_doc["role"]})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "reset_required": user_doc.get("reset_required", False)
    }

@router.patch("/first-login-reset")
async def first_login_reset(
    reset_data: PasswordResetRequest, 
    email: str = Depends(get_current_user_email)
):
    user_doc = await users_collection.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user_doc.get("reset_required", False):
         raise HTTPException(status_code=400, detail="Password reset not required for this user")

    hashed_password = get_password_hash(reset_data.new_password)
    
    await users_collection.update_one(
        {"email": email},
        {"$set": {"hashed_password": hashed_password, "reset_required": False}}
    )
    
    return {"message": "Password updated successfully"}

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        # Return 200 to prevent email enumeration
        return {"message": "If the email exists, a reset link has been sent."}
    
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=15)
    
    await users_collection.update_one(
        {"email": request.email},
        {"$set": {
            "password_reset_token": token,
            "password_reset_expiry": expiry
        }}
    )
    
    # Send Email
    await send_email(
        to_email=request.email,
        subject="Reset Password",
        body=f"Target: {request.email}\nYour reset token is: {token}\nExpires in 15 minutes."
    )
    
    return {"message": "If the email exists, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password_token(request: TokenResetRequest):
    user = await users_collection.find_one({
        "password_reset_token": request.token,
        "password_reset_expiry": {"$gt": datetime.utcnow()} # Expiry must be in future
    })
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    hashed_password = get_password_hash(request.new_password)
    
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": hashed_password,
                "reset_required": False,
                "password_reset_token": None,
                "password_reset_expiry": None
            }
        }
    )
    
    return {"message": "Password updated successfully."}

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    email: str = Depends(get_current_user_email)
):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Verify current password
    if not verify_password(request.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    hashed_password = get_password_hash(request.new_password)
    
    await users_collection.update_one(
        {"email": email},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    return {"message": "Password updated successfully"}
