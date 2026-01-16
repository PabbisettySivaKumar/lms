from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List
from datetime import datetime
import shutil
import os
from bson import ObjectId
from src.db import db
from src.models.policy import Policy, PolicyCreate, PolicyAcknowledgment
from src.models.user import User, UserRole
from src.routes.users import get_current_user
from src.routes.auth import verify_admin

router = APIRouter(prefix="/policies", tags=["Policies"])

# Collections
policies_collection = db["policies"]
acknowledgments_collection = db["policy_acknowledgments"]

# Ensure upload directory exists
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/admin", response_model=Policy)
async def upload_policy(
    title: str = Form(...),
    file: UploadFile = File(...),
    admin: User = Depends(verify_admin)
):
    # Save file
    timestamp = int(datetime.utcnow().timestamp())
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create DB Entry
    policy_doc = {
        "title": title,
        "file_url": f"/static/uploads/{filename}",
        "created_at": datetime.utcnow()
    }
    
    result = await policies_collection.insert_one(policy_doc)
    created_policy = await policies_collection.find_one({"_id": result.inserted_id})
    created_policy["_id"] = str(created_policy["_id"])
    
    return Policy(**created_policy)

@router.get("", response_model=List[Policy])
async def list_policies(current_user: User = Depends(get_current_user)):
    policies = []
    cursor = policies_collection.find().sort("created_at", -1)
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        
        # Check acknowledgment
        ack = await acknowledgments_collection.find_one({
            "user_id": str(current_user.id),
            "policy_id": str(doc["_id"])
        })
        
        doc["is_acknowledged"] = ack is not None
        doc["acknowledged_at"] = ack["acknowledged_at"] if ack else None
        
        policies.append(Policy(**doc))
        
    return policies

@router.post("/{policy_id}/acknowledge")
async def acknowledge_policy(policy_id: str, current_user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(policy_id):
        raise HTTPException(status_code=400, detail="Invalid policy ID")
        
    policy = await policies_collection.find_one({"_id": ObjectId(policy_id)})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    # Check if already acknowledged
    existing = await acknowledgments_collection.find_one({
        "user_id": str(current_user.id),
        "policy_id": policy_id
    })
    
    if existing:
        return {"message": "Already acknowledged"}
        
    ack_doc = {
        "user_id": str(current_user.id),
        "policy_id": policy_id,
        "acknowledged_at": datetime.utcnow()
    }
    
    await acknowledgments_collection.insert_one(ack_doc)
    return {"message": "Policy acknowledged successfully"}

@router.delete("/admin/{policy_id}")
async def delete_policy(policy_id: str, admin: User = Depends(verify_admin)):
    if not ObjectId.is_valid(policy_id):
        raise HTTPException(status_code=400, detail="Invalid policy ID")
        
    policy = await policies_collection.find_one({"_id": ObjectId(policy_id)})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Optional: Delete file from disk
    # try:
    #     filename = policy["file_url"].split('/')[-1]
    #     os.remove(os.path.join(UPLOAD_DIR, filename))
    # except:
    #     pass

    await policies_collection.delete_one({"_id": ObjectId(policy_id)})
    # Also delete acknowledgments? Optional.
    await acknowledgments_collection.delete_many({"policy_id": policy_id})
    
    return {"message": "Policy deleted"}
