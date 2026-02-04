import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.db import AsyncSessionLocal
from backend.models import Policy, UserLeaveBalance, User as UserModel, LeaveTypeEnum, JobLog
from backend.models.enums import BalanceChangeTypeEnum, JobStatusEnum
from backend.services.balance_history import record_balance_change
from sqlalchemy import select, and_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def get_effective_policy(year: int, db: AsyncSession):
    """
    Fetches policy for the given year. 
    If not found, falls back to the most recent previous year (Continuity).
    Defaults if no policies exist at all.
    """
    # 1. Try Specific Year
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    if policy:
        logger.debug("Using defined policy for year=%s", year)
        return {
            "casual_leave_quota": policy.casual_leave_quota,
            "sick_leave_quota": policy.sick_leave_quota,
            "wfh_quota": policy.wfh_quota
        }
        
    # 2. Fallback to Latest Previous Year
    # Find one policy with year < given_year, sorted descending
    result = await db.execute(
        select(Policy)
        .where(Policy.year < year)
        .order_by(Policy.year.desc())
        .limit(1)
    )
    fallback = result.scalar_one_or_none()
    if fallback:
        logger.debug("No policy for year=%s, using fallback year=%s", year, fallback.year)
        return {
            "casual_leave_quota": fallback.casual_leave_quota,
            "sick_leave_quota": fallback.sick_leave_quota,
            "wfh_quota": fallback.wfh_quota
        }
        
    # 3. Hard Default
    logger.debug("No policies found, using system defaults")
    return {
        "casual_leave_quota": 12,
        "sick_leave_quota": 5,
        "wfh_quota": 2
    }

def _monthly_accrual_job_name(year: int, month: int) -> str:
    """Canonical job name for monthly accrual (one per month)."""
    return f"monthly_accrual_{year}_{month:02d}"


async def monthly_accrual():
    """
    Adds 1/12th of Casual Leave Quota to all active employees.
    Runs on the 1st of every month. Idempotent: skips if already run this month.
    """
    now = datetime.datetime.now()
    current_year, current_month = now.year, now.month
    job_name = _monthly_accrual_job_name(current_year, current_month)
    logger.info("Running monthly accrual at %s", now)

    async with AsyncSessionLocal() as db:
        # Idempotency: skip if already run this month
        existing = await db.execute(
            select(JobLog).where(
                and_(JobLog.job_name == job_name, JobLog.status == JobStatusEnum.SUCCESS)
            )
        )
        if existing.scalar_one_or_none():
            logger.info("Monthly accrual already run for %s-%02d, skipping", current_year, current_month)
            return None

        policy = await get_effective_policy(current_year, db)
        casual_quota = policy.get("casual_leave_quota", 12)
        monthly_rate = round(casual_quota / 12, 2)
        logger.info("Accruing %s CL (quota: %s)", monthly_rate, casual_quota)

        result = await db.execute(select(UserModel).where(UserModel.is_active == True))
        active_users = result.scalars().all()
        updated_count = 0
        for user in active_users:
            balance_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(
                        UserLeaveBalance.user_id == user.id,
                        UserLeaveBalance.leave_type == LeaveTypeEnum.CASUAL
                    )
                )
            )
            balance = balance_result.scalar_one_or_none()
            prev = float(balance.balance) if balance else 0.0
            if balance:
                balance.balance = prev + monthly_rate
            else:
                new_balance = UserLeaveBalance(
                    user_id=user.id,
                    leave_type=LeaveTypeEnum.CASUAL,
                    balance=monthly_rate
                )
                db.add(new_balance)
            await record_balance_change(
                db, user.id, LeaveTypeEnum.CASUAL, prev, prev + monthly_rate,
                BalanceChangeTypeEnum.ACCRUAL, reason="Monthly accrual",
                related_leave_id=None, changed_by=None,
            )
            updated_count += 1

        db.add(JobLog(
            job_name=job_name,
            status=JobStatusEnum.SUCCESS,
            details={"users_updated": updated_count, "monthly_rate": monthly_rate},
        ))
        await db.commit()
        logger.info("Monthly accrual complete, updated %s users", updated_count)
        return None

async def yearly_leave_reset():
    """
    Resets leave balances for all employees on Jan 1st.
    Logic:
    - CL: Reset to 0 (Lapses, new accrual starts).
    - SL: Reset to Policy Quota.
    - WFH: Reset to Policy Quota.
    - EL: Reset to 0 (no carry-over).
    """
    logger.info("Running yearly reset at %s", datetime.datetime.now())
    
    async with AsyncSessionLocal() as db:
        current_year = datetime.datetime.now().year
        policy = await get_effective_policy(current_year, db)
        
        sick_quota = float(policy.get("sick_leave_quota", 3))
        wfh_quota = int(policy.get("wfh_quota", 2))
        
        logger.info("Applying yearly reset: SL=%s, WFH=%s, CL=0, EL=0", sick_quota, wfh_quota)

        # Get all users
        result = await db.execute(select(UserModel))
        users = result.scalars().all()
        
        # Process each user's balances
        for user in users:
            # Reset CL, SL, WFH, EL (no carry-over)
            for leave_type, balance_value in [
                (LeaveTypeEnum.CASUAL, 0.0),
                (LeaveTypeEnum.SICK, sick_quota),
                (LeaveTypeEnum.WFH, wfh_quota),
                (LeaveTypeEnum.EARNED, 0.0),
            ]:
                balance_result = await db.execute(
                    select(UserLeaveBalance).where(
                        and_(
                            UserLeaveBalance.user_id == user.id,
                            UserLeaveBalance.leave_type == leave_type
                        )
                    )
                )
                balance = balance_result.scalar_one_or_none()
                prev = float(balance.balance) if balance else 0.0
                if balance:
                    balance.balance = balance_value
                else:
                    new_balance = UserLeaveBalance(
                        user_id=user.id,
                        leave_type=leave_type,
                        balance=balance_value
                    )
                    db.add(new_balance)
                if prev != balance_value:
                    await record_balance_change(
                        db, user.id, leave_type, prev, balance_value,
                        BalanceChangeTypeEnum.YEARLY_RESET, reason="Yearly reset",
                        related_leave_id=None, changed_by=None,
                    )

        await db.commit()
        logger.info("Yearly reset processed for %s users", len(users))
    
    # 3. Trigger Monthly Accrual for the starting month (Jan) or current month (Manual Reset)
    logger.info("Triggering post-reset monthly accrual")
    await monthly_accrual()

    # 4. Record yearly reset in job_logs so manual trigger is locked out for this year
    async with AsyncSessionLocal() as db_log:
        job_name = f"yearly_reset_{current_year}"
        db_log.add(JobLog(
            job_name=job_name,
            status=JobStatusEnum.SUCCESS,
            details={"trigger": "scheduler", "year": current_year},
        ))
        await db_log.commit()

    logger.info("Yearly reset complete")
    return None

def start_scheduler():
    # Trigger: 1st day of month at 00:00
    scheduler.add_job(monthly_accrual, 'cron', day=1, hour=0, minute=0)
    
    # Trigger: Jan 1st at 00:05 (slightly after monthly to allow coordination if needed, or simply same time)
    scheduler.add_job(yearly_leave_reset, 'cron', month=1, day=1, hour=0, minute=5)
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shutdown")
