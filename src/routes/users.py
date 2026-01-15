from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime
from src.db import users_collection
from src.models.user import User, UserCreateAdmin, UserRole
from src.utils.security import get_password_hash
from src.routes.auth import get_current_user_email

router = APIRouter(prefix="", tags=["Users"])

async def get_current_user(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Mapping _id to id happens later via list comprehension or manual assignment if needed,
    # but Pydantic's alias="_id" handles it if we pass the doc.
    # However, 'id' field is used in response model.
    user["_id"] = str(user["_id"])
    return User(**user)

async def verify_admin(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    allowed_roles = [UserRole.ADMIN, UserRole.FOUNDER, UserRole.HR]
    if not user or user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

from src.models.user import UserUpdateProfile

@router.patch("/users/me", response_model=User)
async def update_user_me(
    profile_data: UserUpdateProfile,
    current_user: User = Depends(get_current_user)
):
    update_data = {k: v for k, v in profile_data.dict().items() if v is not None}
    
    # Handle DOB conversion if present
    if update_data.get("dob"):
         update_data["dob"] = str(update_data["dob"])
         
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_data}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)

@router.post("/admin/users", response_model=User)
async def create_user_admin(user_in: UserCreateAdmin, admin=Depends(verify_admin)):
    # Check if email exists
    if await users_collection.find_one({"email": user_in.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check if employee_id exists
    if await users_collection.find_one({"employee_id": user_in.employee_id}):
        raise HTTPException(status_code=400, detail=f"Employee ID {user_in.employee_id} already exists")

    manager_name = None
    if user_in.manager_id:
        manager = await users_collection.find_one({"employee_id": user_in.manager_id})
        if not manager:
            raise HTTPException(status_code=400, detail=f"Manager with ID {user_in.manager_id} not found")
        manager_name = manager["full_name"]
    
    # Default Password
    hashed_password = get_password_hash("Welcome@2026")
    
    user_dict = user_in.dict()
    user_dict.update({
        "hashed_password": hashed_password,
        "is_active": True,
        "reset_required": True,
        "casual_balance": 0.0,
        "sick_balance": 0.0,
        "earned_balance": 0.0,
        "wfh_balance": 0,
        "comp_off_balance": 0.0,
        "manager_name": manager_name
    })
    
    if user_dict.get("joining_date"):
        user_dict["joining_date"] = str(user_dict["joining_date"])

    res = await users_collection.insert_one(user_dict)
    
    created_user = await users_collection.find_one({"_id": res.inserted_id})
    created_user["_id"] = str(created_user["_id"])
    return User(**created_user)

@router.get("/admin/managers", response_model=List[dict])
async def list_managers(admin=Depends(verify_admin)):
    managers = []
    # Find users who are managers, HR, or founders
    query = {"role": {"$in": [UserRole.MANAGER, UserRole.HR, UserRole.FOUNDER]}}
    cursor = users_collection.find(query)
    async for doc in cursor:
        managers.append({
            "employee_id": doc["employee_id"],
            "full_name": doc["full_name"],
            "role": doc["role"]
        })
    return managers

@router.get("/admin/users", response_model=List[User])
async def list_users(admin=Depends(verify_admin)):
    users = []
    cursor = users_collection.find({})
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        users.append(User(**doc))
    return users

from bson import ObjectId
from src.models.user import UserBalanceUpdate

@router.patch("/admin/users/{user_id}/balance", response_model=User)
async def update_user_balance(user_id: str, balance_data: UserBalanceUpdate, admin=Depends(verify_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = {k: v for k, v in balance_data.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No balance fields provided")
        
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)

from src.services.scheduler import monthly_accrual

@router.post("/admin/trigger-accrual")
async def trigger_accrual(admin=Depends(verify_admin)):
    """
    Manually trigger the monthly accrual process (for testing).
    """
    await monthly_accrual()
    return {"message": "Monthly accrual triggered successfully"}

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin=Depends(verify_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "User deleted successfully"}

from src.models.user import UserUpdateAdmin

@router.patch("/admin/users/{user_id}", response_model=User)
async def update_user_details(
    user_id: str, 
    user_data: UserUpdateAdmin, 
    admin=Depends(verify_admin)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    existing_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = {k: v for k, v in user_data.dict().items() if v is not None}

    # Handle manager linking if manager_id changed or set
    if "manager_id" in update_dict and update_dict["manager_id"]:
        manager = await users_collection.find_one({"employee_id": update_dict["manager_id"]})
        if not manager:
             raise HTTPException(status_code=400, detail=f"Manager ID {update_dict['manager_id']} not found")
        update_dict["manager_name"] = manager["full_name"]
    elif "manager_id" in update_dict and update_dict["manager_id"] is None:
        update_dict["manager_name"] = None

    if "joining_date" in update_dict:
        update_dict["joining_date"] = str(update_dict["joining_date"])

    if not update_dict:
         return User(**{**existing_user, "_id": str(existing_user["_id"])})

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)
