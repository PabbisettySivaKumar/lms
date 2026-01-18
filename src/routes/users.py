from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime
from src.db import users_collection, db
from src.models.user import User, UserCreateAdmin, UserRole
from src.utils.security import get_password_hash
from src.routes.auth import get_current_user_email, verify_admin
from fastapi import UploadFile, File
import shutil
from pathlib import Path
import os

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
    if update_data.get("father_dob"):
         update_data["father_dob"] = str(update_data["father_dob"])
    if update_data.get("mother_dob"):
         update_data["mother_dob"] = str(update_data["mother_dob"])
    if update_data.get("spouse_dob"):
         update_data["spouse_dob"] = str(update_data["spouse_dob"])
         
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_data}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    updated_user["_id"] = str(updated_user["_id"])
    updated_user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)

@router.post("/users/me/profile-picture", response_model=User)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
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
    
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"profile_picture_url": full_url}}
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
    
    # Password Handling
    if len(user_in.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    hashed_password = get_password_hash(user_in.password)
    
    # Fetch active policy
    current_year = datetime.now().year
    policy = await db.policies.find_one({"year": current_year})
    
    # Defaults
    sick_quota = 3.0
    wfh_quota = 0
    casual_quota = 12.0 # Default yearly quota
    
    if policy:
        sick_quota = float(policy.get("sick_leave_quota", 3.0))
        wfh_quota = int(policy.get("wfh_quota", 0))
        casual_quota = float(policy.get("casual_leave_quota", 12.0))

    initial_cl = casual_quota / 12.0

    user_dict = user_in.dict()
    user_dict.update({
        "hashed_password": hashed_password,
        "is_active": True,
        "reset_required": True,
        "casual_balance": initial_cl,
        "sick_balance": sick_quota,
        "earned_balance": 0.0,
        "wfh_balance": wfh_quota,
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
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No balance fields provided")
        
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)

@router.post("/users/me/documents", response_model=User)
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    
    # Create documents directory
    UPLOAD_DIR = Path(f"static/uploads/documents/{current_user.id}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    new_docs = []
    
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            continue # Skip invalid files or raise error? Let's skip for now or better, raise if any invalid?
            # User experience: better to probably allow valid ones or fail all? 
            # Let's simple fail if any checks fail for safety
            # raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")
        
        # Unique filename to prevent overwrite
        timestamp = int(datetime.now().timestamp())
        safe_filename = file.filename.replace(" ", "_")
        saved_filename = f"{timestamp}_{safe_filename}"
        file_path = UPLOAD_DIR / saved_filename
        
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
            
        new_docs.append({
            "name": file.filename,
            "url": f"/static/uploads/documents/{current_user.id}/{saved_filename}",
            "saved_filename": saved_filename, # Used for deletion
            "uploaded_at": datetime.now().isoformat()
        })
        
    if new_docs:
        await users_collection.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$push": {"documents": {"$each": new_docs}}}
        )
        
    updated_user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    updated_user["_id"] = str(updated_user["_id"])
    return User(**updated_user)

@router.delete("/users/me/documents/{filename}", response_model=User)
async def delete_document(filename: str, current_user: User = Depends(get_current_user)):
    # Find document to get saved path
    # Actually we stored 'saved_filename' in the dict, but we are passing 'saved_filename' as param?
    # Or passing original name? Usually passing ID or unique saved_filename is safer.
    # Let's assume frontend passes the 'saved_filename'.
    
    # Verify file belongs to user
    user_doc = await users_collection.find_one(
        {"_id": ObjectId(current_user.id), "documents.saved_filename": filename}
    )
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Remove from disk
    file_path = Path(f"static/uploads/documents/{current_user.id}/{filename}")
    if file_path.exists():
        os.remove(file_path)
        
    # Remove from DB
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$pull": {"documents": {"saved_filename": filename}}}
    )
    
    updated_user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
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
    if updated_user:
        updated_user["_id"] = str(updated_user["_id"])
        return User(**updated_user)
    
    raise HTTPException(status_code=404, detail="User not found after update")

@router.get("/admin/integrity-check")
async def check_data_integrity(admin=Depends(verify_admin)):
    pipeline = [
        {"$group": {
            "_id": "$email",
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"}
        }},
        {"$match": {
            "count": {"$gt": 1}
        }}
    ]
    
    duplicates = []
    cursor = users_collection.aggregate(pipeline)
    async for doc in cursor:
        # Fetch details for these IDs
        details = []
        for uid in doc['ids']:
             user = await users_collection.find_one({"_id": uid})
             if user:
                 details.append({
                     "id": str(user["_id"]),
                     "name": user.get("full_name"),
                     "role": user.get("role"),
                     "is_active": user.get("is_active")
                 })
                 
        duplicates.append({
            "email": doc["_id"],
            "count": doc["count"],
            "accounts": details
        })
        
    return {"status": "issues_found" if duplicates else "healthy", "duplicates": duplicates}
