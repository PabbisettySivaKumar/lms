from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
import shutil
import os
from pathlib import Path
from src.db import db
from src.models.policy import LeavePolicy, PolicyDocument
from src.routes.users import get_current_user
from src.models.user import User, UserRole
from typing import List
from datetime import datetime

router = APIRouter(prefix="/policies", tags=["Policies"])

policies_collection = db.policies
acknowledgments_collection = db.policy_acknowledgments

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
    name: str = None,
    file: UploadFile = File(...), 
    current_user: User = Depends(verify_admin)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # If policy doesn't exist, create one with defaults
    policy = await policies_collection.find_one({"year": year})
    if not policy:
        default_policy = {
            "year": year,
            "casual_leave_quota": 12,
            "sick_leave_quota": 5,
            "wfh_quota": 2,
            "is_active": True,
            "documents": []
        }
        await policies_collection.insert_one(default_policy)
        
    UPLOAD_DIR = Path("static/uploads/policies")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = f"{year}_{int(datetime.now().timestamp())}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / filename
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
        
    document_url = f"/static/uploads/policies/{filename}"
    doc_display_name = name if name else file.filename
    new_doc = PolicyDocument(
        name=doc_display_name,
        url=document_url,
        uploaded_at=datetime.utcnow()
    )
    
    await policies_collection.update_one(
        {"year": year},
        {
            "$push": {"documents": new_doc.dict()},
            "$set": {
                # Update legacy fields to the LATEST uploaded document for compatibility
                "document_url": document_url, 
                "document_name": doc_display_name
            }
        }
    )
    
    updated = await policies_collection.find_one({"year": year})
    updated["_id"] = str(updated["_id"])
    return LeavePolicy(**updated)

@router.delete("/{year}/document", response_model=LeavePolicy)
async def delete_policy_document(
    year: int, 
    url: str,
    current_user: User = Depends(verify_admin)
):
    # Check if policy exists
    policy = await policies_collection.find_one({"year": year})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    # Remove from disk
    # Extract filename from URL
    # URL: /static/uploads/policies/filename
    if "/static/uploads/policies/" in url:
        filename = url.split("/static/uploads/policies/")[1]
        file_path = Path("static/uploads/policies") / filename
        if file_path.exists():
            os.remove(file_path)
    
    # Remove from DB
    await policies_collection.update_one(
        {"year": year},
        {"$pull": {"documents": {"url": url}}}
    )
    
    # Check if legacy fields need clearing if this was the last one?
    # Or if the deleted one matched the legacy one.
    # For now, let's keep it simple. If documents list becomes empty, we could clear legacy.
    
    updated = await policies_collection.find_one({"year": year})
    updated["_id"] = str(updated["_id"])
    return LeavePolicy(**updated)

@router.delete("/{year}")
async def delete_entire_policy(
    year: int, 
    current_user: User = Depends(verify_admin)
):
    # Find policy to get documents for disk cleanup
    policy = await policies_collection.find_one({"year": year})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Clean up files from disk
    if "documents" in policy:
        for doc in policy["documents"]:
            url = doc.get("url")
            if url and "/static/uploads/policies/" in url:
                filename = url.split("/static/uploads/policies/")[1]
                file_path = Path("static/uploads/policies") / filename
                if file_path.exists():
                    os.remove(file_path)
    
    # Delete from DB
    await policies_collection.delete_one({"year": year})
    return {"message": f"Policy for year {year} deleted successfully"}

@router.post("/{year}/acknowledge")
async def acknowledge_policy(
    year: int,
    document_url: str,
    current_user: User = Depends(get_current_user)
):
    # Check if policy exists for that year
    policy = await policies_collection.find_one({"year": year})
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy for year {year} not found")

    # Save or update acknowledgment for this specific document
    await acknowledgments_collection.update_one(
        {"user_id": str(current_user.id), "year": year, "document_url": document_url},
        {"$set": {
            "user_id": str(current_user.id),
            "full_name": current_user.full_name,
            "email": current_user.email,
            "year": year,
            "document_url": document_url,
            "acknowledged_at": datetime.utcnow()
        }},
        upsert=True
    )
    return {"message": "Document acknowledged successfully"}

@router.get("/{year}/my-acknowledgments")
async def get_my_acknowledgments(
    year: int,
    current_user: User = Depends(get_current_user)
):
    acks_cursor = acknowledgments_collection.find({
        "user_id": str(current_user.id),
        "year": year
    })
    acks = await acks_cursor.to_list(length=100)
    for a in acks:
        a["_id"] = str(a["_id"])
    return acks

@router.get("/{year}/report")
async def get_acknowledgment_report(
    year: int,
    current_user: User = Depends(verify_admin)
):
    # Get the policy to know total documents
    policy = await policies_collection.find_one({"year": year})
    total_docs = len(policy.get("documents", [])) if policy else 0
    if not policy and total_docs == 0:
        # Check legacy field if needed, but we mostly care about documents list now
        if policy and policy.get("document_url"):
            total_docs = 1

    # Get all active employees
    users_cursor = db.users.find({"is_active": True})
    users = await users_cursor.to_list(length=1000)
    
    # Get all acknowledgments for this year
    acks_cursor = acknowledgments_collection.find({"year": year})
    acks = await acks_cursor.to_list(length=5000)
    
    # Group acknowledgments by user
    ack_map = {}
    for a in acks:
        uid = a["user_id"]
        if uid not in ack_map:
            ack_map[uid] = []
        ack_map[uid].append(a)
    
    report = []
    for user in users:
        user_id = str(user["_id"])
        user_acks = ack_map.get(user_id, [])
        acknowledged_count = len(user_acks)
        
        report.append({
            "user_id": user_id,
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "acknowledged_count": acknowledged_count,
            "total_documents": total_docs,
            "fully_acknowledged": acknowledged_count >= total_docs if total_docs > 0 else False,
            "acknowledgments": [
                {"document_url": a["document_url"], "acknowledged_at": a["acknowledged_at"]}
                for a in user_acks
            ]
        })
    
    return report
