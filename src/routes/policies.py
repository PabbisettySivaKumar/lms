from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
import shutil
import os
from pathlib import Path
from src.db import db
from src.models.policy import LeavePolicy
from src.routes.users import get_current_user
from src.models.user import User, UserRole
from typing import List
from datetime import datetime

router = APIRouter(prefix="/policies", tags=["Policies"])

policies_collection = db.policies

# Helper to verify admin
def verify_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.HR, UserRole.FOUNDER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted"
        )
    return current_user

@router.get("/active", response_model=LeavePolicy)
async def get_active_policy():
    current_year = datetime.now().year
    
    # Try to find policy for current year
    policy = await policies_collection.find_one({"year": current_year})
    
    if policy:
        policy["_id"] = str(policy["_id"])
        return LeavePolicy(**policy)
        
    # Fallback to default policy if none found
    default_policy = {
        "year": current_year,
        "casual_leave_quota": 12,
        "sick_leave_quota": 5,
        "wfh_quota": 2,
        "is_active": True
    }
    return LeavePolicy(**default_policy)

@router.get("/", response_model=List[LeavePolicy])
async def get_all_policies(current_user: User = Depends(verify_admin)):
    policies = []
    async for p in policies_collection.find().sort("year", -1):
        p["_id"] = str(p["_id"])
        policies.append(LeavePolicy(**p))
    return policies

@router.post("/", response_model=LeavePolicy)
async def create_or_update_policy(policy_data: LeavePolicy, current_user: User = Depends(verify_admin)):
    # Check if policy exists for the year
    existing = await policies_collection.find_one({"year": policy_data.year})
    
    update_data = policy_data.dict(exclude={"id"})
    
    if existing:
        await policies_collection.update_one(
            {"year": policy_data.year},
            {"$set": update_data}
        )
        pid = existing["_id"]
    else:
        result = await policies_collection.insert_one(update_data)
        pid = result.inserted_id
        
    updated = await policies_collection.find_one({"_id": pid})
    updated["_id"] = str(updated["_id"])
    return LeavePolicy(**updated)

@router.post("/{year}/document", response_model=LeavePolicy)
async def upload_policy_document(
    year: int, 
    file: UploadFile = File(...), 
    current_user: User = Depends(verify_admin)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check if policy exists
    policy = await policies_collection.find_one({"year": year})
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy for year {year} not found. Please save the policy first.")
        
    UPLOAD_DIR = Path("static/uploads/policies")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = f"{year}_policy.pdf"
    file_path = UPLOAD_DIR / filename
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
        
    document_url = f"/static/uploads/policies/{filename}"
    
    await policies_collection.update_one(
        {"year": year},
        {"$set": {"document_url": document_url}}
    )
    
    updated = await policies_collection.find_one({"year": year})
    updated["_id"] = str(updated["_id"])
    return LeavePolicy(**updated)
