from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from src.db import db, users_collection
from src.models.leave import CompOffClaim, CompOffClaimCreate, CompOffStatus
from src.routes.auth import get_current_user_email
from src.models.user import UserRole
from bson import ObjectId

router = APIRouter(prefix="/leaves", tags=["Comp-Off"])
comp_off_collection = db["comp_off_claims"]

async def get_current_user(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def verify_manager(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    if not user or user["role"] not in [UserRole.MANAGER, UserRole.ADMIN, UserRole.FOUNDER]:
        raise HTTPException(status_code=403, detail="Manager access required")
    return user

@router.post("/claim-comp-off", response_model=dict)
async def claim_comp_off(claim: CompOffClaimCreate, user=Depends(get_current_user)):
    if claim.work_date > date.today():
        raise HTTPException(status_code=400, detail="Cannot claim comp-off for future dates")
    
    claim_dict = claim.dict()
    claim_dict["claimant_id"] = str(user["_id"])
    claim_dict["status"] = CompOffStatus.PENDING
    # Store date as string for consistency if needed, or keeping as date object if using correct Mongo codec
    # Using string YYYY-MM-DD for simplicity across the board
    claim_dict["work_date"] = str(claim.work_date)
    
    res = await comp_off_collection.insert_one(claim_dict)
    return {"message": "Comp-off claim submitted", "id": str(res.inserted_id)}

@router.patch("/claim-action/{claim_id}")
async def action_comp_off(claim_id: str, action: str, approver=Depends(verify_manager)):
    if action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    claim = await comp_off_collection.find_one({"_id": ObjectId(claim_id)})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim["status"] != CompOffStatus.PENDING:
        raise HTTPException(status_code=400, detail="Claim is not pending")
    
    new_status = CompOffStatus.APPROVED if action == "APPROVE" else CompOffStatus.REJECTED
    
    await comp_off_collection.update_one(
        {"_id": ObjectId(claim_id)},
        {"$set": {"status": new_status, "approver_id": str(approver["_id"])}}
    )
    
    if new_status == CompOffStatus.APPROVED:
        # Increment user's comp-off balance
        await users_collection.update_one(
            {"_id": ObjectId(claim["claimant_id"])},
            {"$inc": {"comp_off_balance": 1.0}}
        )
        
    return {"message": f"Claim {new_status}"}
