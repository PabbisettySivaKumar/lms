from fastapi import APIRouter, HTTPException, Depends, Response, Request, status
from typing import List
from backend.db import get_db, AsyncSessionLocal
from backend.services.audit import log_action as audit_log_action
from backend.utils.action_log import log_user_action
from backend.models import Holiday as HolidayModel, JobLog as JobLogModel, JobStatusEnum
from backend.models.leave import Holiday, HolidayCreate
from backend.models.user import UserRole
from backend.routes.auth import get_current_user_email, verify_admin
from backend.routes.users import get_current_user
from backend.models.user import User
from sqlalchemy import select, and_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from backend.utils.id_utils import to_int_id
from datetime import datetime
from backend.models.job import JobLog
from backend.services.scheduler import yearly_leave_reset

router = APIRouter(prefix="/admin", tags=["Holidays"])

calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.post("/holidays/bulk", response_model=dict)
async def bulk_create_holidays(
    request: Request,
    holidays: List[HolidayCreate],
    admin=Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
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

    admin_id = admin.get("id") if isinstance(admin, dict) else getattr(admin, "id", None)
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    await audit_log_action(
        db,
        "BULK_CREATE_HOLIDAYS",
        "HOLIDAY",
        user_id=admin_id,
        new_values={"count": inserted_count, "errors": errors},
        actor_email=admin_email,
        actor_employee_id=admin_emp_id,
        actor_full_name=admin_name,
        summary=f"{admin_name or 'Admin'} bulk created {inserted_count} holiday(s)" if admin_name else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    log_user_action(
        "BULK_CREATE_HOLIDAYS",
        user_id=admin_id,
        email=admin_email,
        employee_id=admin_emp_id,
        full_name=admin_name,
        count=inserted_count,
        errors_count=len(errors),
    )
        
    return {
        "success": True, 
        "count": inserted_count,
        "errors": errors
    }

@router.post("/holidays", response_model=str)
async def create_holiday(
    request: Request,
    holiday: HolidayCreate,
    admin=Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
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
    admin_id = admin.get("id") if isinstance(admin, dict) else getattr(admin, "id", None)
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    await audit_log_action(
        db,
        "CREATE_HOLIDAY",
        "HOLIDAY",
        user_id=admin_id,
        affected_entity_id=holiday_id,
        new_values={"date": str(holiday.date), "name": holiday.name},
        actor_email=admin_email,
        actor_employee_id=admin_emp_id,
        actor_full_name=admin_name,
        summary=f"{admin_name or 'Admin'} created holiday {holiday.name} ({holiday.date})" if admin_name else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    log_user_action(
        "CREATE_HOLIDAY",
        user_id=admin_id,
        email=admin_email,
        employee_id=admin_emp_id,
        full_name=admin_name,
        holiday_id=holiday_id,
        date=str(holiday.date),
        name=holiday.name,
    )
    return str(holiday_id)

@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    request: Request,
    holiday_id: str,
    admin=Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    holiday_id_int = to_int_id(holiday_id)
    if not holiday_id_int:
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    result = await db.execute(select(HolidayModel).where(HolidayModel.id == holiday_id_int))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")

    admin_id = admin.get("id") if isinstance(admin, dict) else getattr(admin, "id", None)
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    await audit_log_action(
        db,
        "DELETE_HOLIDAY",
        "HOLIDAY",
        user_id=admin_id,
        affected_entity_id=holiday.id,
        old_values={"date": str(holiday.date), "name": holiday.name},
        actor_email=admin_email,
        actor_employee_id=admin_emp_id,
        actor_full_name=admin_name,
        summary=f"{admin_name or 'Admin'} deleted holiday {holiday.name} ({holiday.date})" if admin_name else None,
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.delete(holiday)
    await db.commit()
    admin_email = admin.get("email") if isinstance(admin, dict) else getattr(admin, "email", None)
    admin_name = admin.get("full_name") if isinstance(admin, dict) else getattr(admin, "full_name", None)
    admin_emp_id = admin.get("employee_id") if isinstance(admin, dict) else getattr(admin, "employee_id", None)
    log_user_action(
        "DELETE_HOLIDAY",
        user_id=admin_id,
        email=admin_email,
        employee_id=admin_emp_id,
        full_name=admin_name,
        holiday_id=holiday.id,
        date=str(holiday.date),
        name=holiday.name,
    )
    return {"message": "Deleted successfully"}

@router.post("/yearly-reset")
async def run_yearly_reset(
    request: Request,
    current_user: dict = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Resets leave balances for the new year.
    - Casual/Sick Leave: Lapse and set to 12.0
    - Earned Leave: Carry forward 50% of current balance (Exact decimal).
    Locked out if yearly reset has already run for the current year.
    """
    current_year = datetime.utcnow().year
    yearly_scheduler_name = f"yearly_reset_{current_year}"
    yearly_manual_prefix = f"manual_yearly_reset_{current_year}_"

    # Lockout: only allow if yearly reset has not run for this year (scheduler or manual)
    scheduler_run = await db.execute(
        select(JobLogModel).where(
            and_(JobLogModel.job_name == yearly_scheduler_name, JobLogModel.status == JobStatusEnum.SUCCESS)
        )
    )
    manual_run = await db.execute(
        select(JobLogModel).where(
            JobLogModel.job_name.like(f"{yearly_manual_prefix}%"),
            JobLogModel.status == JobStatusEnum.SUCCESS,
        ).limit(1)
    )
    if scheduler_run.scalar_one_or_none() or manual_run.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Yearly reset has already run for {current_year}. Use only when the automatic run (Jan 1) did not happen.",
        )

    timestamp = int(datetime.utcnow().timestamp())
    job_name = f"manual_yearly_reset_{current_year}_{timestamp}"
    executed_at = datetime.utcnow()

    # Execution Logic
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
        admin_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
        admin_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
        admin_name = current_user.get("full_name") if isinstance(current_user, dict) else getattr(current_user, "full_name", None)
        admin_emp_id = current_user.get("employee_id") if isinstance(current_user, dict) else getattr(current_user, "employee_id", None)
        await audit_log_action(
            db,
            "YEARLY_RESET",
            "JOB",
            user_id=admin_id,
            new_values={"job_name": job_name, "year": current_year},
            actor_email=admin_email,
            actor_employee_id=admin_emp_id,
            actor_full_name=admin_name,
            summary=f"{admin_name or 'Admin'} triggered yearly reset for {current_year}",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        admin_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
        admin_name = current_user.get("full_name") if isinstance(current_user, dict) else getattr(current_user, "full_name", None)
        admin_emp_id = current_user.get("employee_id") if isinstance(current_user, dict) else getattr(current_user, "employee_id", None)
        log_user_action(
            "YEARLY_RESET",
            user_id=admin_id,
            email=admin_email,
            employee_id=admin_emp_id,
            full_name=admin_name,
            job_name=job_name,
            year=current_year,
        )
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
