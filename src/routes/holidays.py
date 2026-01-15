from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.db import db
from src.models.leave import Holiday, HolidayCreate
from src.models.user import UserRole
from src.routes.auth import get_current_user_email, users_collection

router = APIRouter(prefix="/admin", tags=["Holidays"])
calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])

holidays_collection = db["holidays"]

async def verify_admin(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    allowed_roles = [UserRole.ADMIN, UserRole.FOUNDER, UserRole.HR]
    if not user or user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Admin/HR access required")
    return user

@router.post("/holidays/bulk", response_model=dict)
async def bulk_create_holidays(holidays: List[HolidayCreate], admin=Depends(verify_admin)):
    """
    Bulk import holidays. Skips duplicates based on date.
    """
    inserted_count = 0
    errors = []
    
    for h in holidays:
        # Check if exists
        existing = await holidays_collection.find_one({"date": str(h.date)})
        if existing:
            errors.append(f"Date {h.date} already exists")
            continue
            
        h_dict = h.dict()
        h_dict["date"] = str(h.date)
        await holidays_collection.insert_one(h_dict)
        inserted_count += 1
        
    return {
        "success": True, 
        "count": inserted_count,
        "errors": errors
    }

@router.post("/holidays", response_model=str)
async def create_holiday(holiday: HolidayCreate, admin=Depends(verify_admin)):
    # Check if exists
    existing = await holidays_collection.find_one({"date": str(holiday.date)})
    if existing:
        raise HTTPException(status_code=400, detail="Holiday for this date already exists")
    
    h_dict = holiday.dict()
    h_dict["date"] = str(holiday.date)
    res = await holidays_collection.insert_one(h_dict)
    return str(res.inserted_id)

@router.get("/holidays", response_model=List[Holiday])
async def list_holidays_admin(admin=Depends(verify_admin)):
    # Retrieve all holidays sorted by date
    holidays = []
    cursor = holidays_collection.find({}).sort("date", 1)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        holidays.append(Holiday(**doc))
    return holidays

from bson import ObjectId

@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, admin=Depends(verify_admin)):
    if not ObjectId.is_valid(holiday_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    res = await holidays_collection.delete_one({"_id": ObjectId(holiday_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
        
    return {"message": "Deleted successfully"}

@calendar_router.get("/holidays", response_model=List[Holiday])
async def get_holidays():
    holidays = []
    # Sort by date for calendar convenience
    cursor = holidays_collection.find({}).sort("date", 1)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        holidays.append(Holiday(**doc))
    return holidays
