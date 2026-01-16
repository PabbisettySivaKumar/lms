from fastapi import APIRouter, HTTPException, Depends
from pymongo import UpdateOne
from typing import List
from src.db import db, job_logs_collection
from src.models.leave import Holiday, HolidayCreate
from src.models.user import UserRole
from src.routes.auth import get_current_user_email, verify_admin, users_collection

router = APIRouter(prefix="/admin", tags=["Holidays"])
calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])

holidays_collection = db["holidays"]



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

from datetime import datetime
from src.db import job_logs_collection, job_logs_collection # Need job_logs
from src.models.job import JobLog

@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, admin=Depends(verify_admin)):
    if not ObjectId.is_valid(holiday_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    res = await holidays_collection.delete_one({"_id": ObjectId(holiday_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
        
    return {"message": "Deleted successfully"}

@router.post("/yearly-reset")
async def run_yearly_reset(current_user: dict = Depends(verify_admin)):
    """
    Resets leave balances for the new year.
    - Casual/Sick Leave: Lapse and set to 12.0
    - Earned Leave: Carry forward 50% of current balance (Exact decimal).
    - Idempotent: Runs only once per year.
    """
    
    # 1. Determine Job Name (YearlyReset_YYYY)
    current_year = datetime.utcnow().year
    next_year = current_year # If I run it in Jan 2026, it is reset FOR 2026.
    
    job_name = f"yearly_reset_{next_year}"
    
    # 2. Idempotency Check
    existing_job = await job_logs_collection.find_one({"job_name": job_name, "status": "SUCCESS"})
    if existing_job:
        return {
            "message": f"Job {job_name} has already been executed successfully.",
            "executed_at": existing_job["executed_at"]
        }
        
    # 3. Execution Logic
    executed_at = datetime.utcnow()
    logs = []
    operations = []
    updated_count = 0
    
    try:
        # Fetch all active users
        async for user in users_collection.find({"is_active": True}):
            old_el = user.get("earned_balance", 0.0)
            
            # Logic
            new_cl = 12.0
            new_sl = 12.0
            new_el = old_el / 2.0 # Exact float division, no rounding
            
            # Prepare Bulk Operation
            operations.append(
                UpdateOne(
                    {"_id": user["_id"]},
                    {"$set": {
                        "casual_balance": new_cl,
                        "sick_balance": new_sl,
                        "earned_balance": new_el
                    }}
                )
            )
            
            logs.append(f"User {user['email']}: EL {old_el} -> {new_el}")
            updated_count += 1
            
        # Execute Bulk Write
        if operations:
            await users_collection.bulk_write(operations)
            
        # 4. Success Log
        job_log = JobLog(
            job_name=job_name,
            status="SUCCESS",
            executed_at=executed_at,
            executed_by=current_user["email"],
            details={
                "users_processed": updated_count,
                "notes": "Reset CL/SL to 12. Halved EL.",
                "sample_logs": logs[:50] # Store first 50 for audit
            }
        )
        await job_logs_collection.insert_one(job_log.dict(by_alias=True))
        
        return {
            "message": "Yearly reset completed successfully.",
            "users_processed": updated_count,
            "job_id": job_name
        }
        
    except Exception as e:
        # 5. Failure Log
        job_log = JobLog(
            job_name=job_name,
            status="FAILED",
            executed_at=executed_at,
            executed_by=current_user["email"],
            details={"error": str(e)}
        )
        await job_logs_collection.insert_one(job_log.dict(by_alias=True))
        raise HTTPException(status_code=500, detail=f"Job failed: {str(e)}")

@calendar_router.get("/holidays", response_model=List[Holiday])
async def get_holidays():
    holidays = []
    # Sort by date for calendar convenience
    cursor = holidays_collection.find({}).sort("date", 1)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        holidays.append(Holiday(**doc))
    return holidays
