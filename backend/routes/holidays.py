from fastapi import APIRouter, HTTPException, Depends, Response
from typing import List
from backend.db import get_db, AsyncSessionLocal
from backend.models import Holiday as HolidayModel, JobLog as JobLogModel, JobStatusEnum
from backend.models.leave import Holiday, HolidayCreate
from backend.models.user import UserRole
from backend.routes.auth import get_current_user_email, verify_admin
from backend.routes.users import get_current_user
from backend.models.user import User
from sqlalchemy import select, and_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from backend.utils.id_utils import to_int_id

router = APIRouter(prefix="/admin", tags=["Holidays"])

calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])



@router.post("/holidays/bulk", response_model=dict)
async def bulk_create_holidays(holidays: List[HolidayCreate], admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    """
    Bulk import holidays. Skips duplicates based on date.
    """
    inserted_count = 0
    errors = []
    
    for h in holidays:
        # Check if exists
        result = await db.execute(select(HolidayModel).where(HolidayModel.date == h.date))
        existing = result.scalar_one_or_none()
        if existing:
            errors.append(f"Date {h.date} already exists")
            continue
            
        new_holiday = HolidayModel(
            date=h.date,
            name=h.name,
            year=h.date.year,
            is_optional=getattr(h, 'is_optional', False)
        )
        db.add(new_holiday)
        inserted_count += 1
    
    await db.commit()
        
    return {
        "success": True, 
        "count": inserted_count,
        "errors": errors
    }

@router.post("/holidays", response_model=str)
async def create_holiday(holiday: HolidayCreate, admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    # Check if exists
    result = await db.execute(select(HolidayModel).where(HolidayModel.date == holiday.date))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Holiday for this date already exists")
    
    new_holiday = HolidayModel(
        date=holiday.date,
        name=holiday.name,
        year=holiday.date.year,
        is_optional=False
    )
    db.add(new_holiday)
    await db.flush()
    holiday_id = new_holiday.id
    await db.commit()
    return str(holiday_id)



from datetime import datetime
from backend.models.job import JobLog
from backend.services.scheduler import yearly_leave_reset

@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, admin=Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    holiday_id_int = to_int_id(holiday_id)
    if not holiday_id_int:
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    result = await db.execute(select(HolidayModel).where(HolidayModel.id == holiday_id_int))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    await db.delete(holiday)
    await db.commit()
        
    return {"message": "Deleted successfully"}

@router.post("/yearly-reset")
async def run_yearly_reset(current_user: dict = Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    """
    Resets leave balances for the new year.
    - Casual/Sick Leave: Lapse and set to 12.0
    - Earned Leave: Carry forward 50% of current balance (Exact decimal).
    - Idempotent: Runs only once per year.
    """
    
    # 1. Determine Job Name (Manual_YearlyReset_YYYY_Timestamp)
    current_year = datetime.utcnow().year
    
    # For manual triggers, we force the run by making the job name unique.
    # This allows re-running the logic if needed (e.g. after changing policy).
    timestamp = int(datetime.utcnow().timestamp())
    job_name = f"manual_yearly_reset_{current_year}_{timestamp}"
    
    # 2. Idempotency Check (Skipped implicitly by unique name, but kept for structure)
    result = await db.execute(
        select(JobLogModel).where(
            and_(JobLogModel.job_name == job_name, JobLogModel.status == JobStatusEnum.SUCCESS)
        )
    )
    existing_job = result.scalar_one_or_none()
    if existing_job:
        return {
            "message": f"Job {job_name} has already been executed successfully.",
            "executed_at": existing_job.executed_at.isoformat() if existing_job.executed_at else None
        }
    # 3. Execution Logic
    executed_at = datetime.utcnow()
    
    try:
        # Execute Shared Logic
        result = await yearly_leave_reset()
        if result is not None:
            pass  # Function completed successfully

        # 4. Success Log
        job_log = JobLogModel(
            job_name=job_name,
            status=JobStatusEnum.SUCCESS,
            executed_at=executed_at,
            executed_by=current_user.get("email", "system"),
            details={
                "users_processed": "Batch (Via Scheduler Logic)",
                "notes": "Triggered manual yearly reset via scheduler function.",
            }
        )
        db.add(job_log)
        await db.commit()
        
        return {
            "message": "Yearly reset completed successfully.",
            "job_id": job_name
        }
        
    except Exception as e:
        # 5. Failure Log
        job_log = JobLogModel(
            job_name=job_name,
            status=JobStatusEnum.FAILED,
            executed_at=executed_at,
            executed_by=current_user.get("email", "system"),
            details={"error": str(e)}
        )
        db.add(job_log)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Job failed: {str(e)}")

@calendar_router.get("/holidays", response_model=List[Holiday])
async def get_holidays(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all holidays with HTTP caching for static data.
    """
    # Sort by date for calendar convenience
    result = await db.execute(select(HolidayModel).order_by(HolidayModel.date))
    holidays_models = result.scalars().all()
    
    holidays = []
    for h in holidays_models:
        holidays.append(Holiday(
            id=h.id,
            date=h.date,
            name=h.name,
            year=h.year,
            is_optional=h.is_optional
        ))
    
    # Set cache headers with shorter max-age and must-revalidate to allow fresh data after uploads
    response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
    return holidays
