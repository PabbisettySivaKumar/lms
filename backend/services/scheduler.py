from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.db import AsyncSessionLocal
from backend.models import Policy, UserLeaveBalance, User as UserModel, LeaveTypeEnum
from sqlalchemy import select, and_  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
import datetime

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
        print(f"[Policy] Using defined policy for {year}")
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
        print(f"[Policy] No policy for {year}. Continuing with {fallback.year} policy.")
        return {
            "casual_leave_quota": fallback.casual_leave_quota,
            "sick_leave_quota": fallback.sick_leave_quota,
            "wfh_quota": fallback.wfh_quota
        }
        
    # 3. Hard Default
    print(f"[Policy] No policies found. Using system defaults.")
    return {
        "casual_leave_quota": 12,
        "sick_leave_quota": 5,
        "wfh_quota": 2
    }

async def monthly_accrual():
    """
    Adds 1/12th of Casual Leave Quota to all active employees.
    Runs on the 1st of every month.
    """
    print(f"--- [Scheduler] Running Monthly Accrual: {datetime.datetime.now()} ---")
    
    async with AsyncSessionLocal() as db:
        current_year = datetime.datetime.now().year
        policy = await get_effective_policy(current_year, db)
        
        casual_quota = policy.get("casual_leave_quota", 12)
        monthly_rate = round(casual_quota / 12, 2)
        
        print(f"[Scheduler] Accruing {monthly_rate} CL (Quota: {casual_quota})")
        
        # Get all active users
        result = await db.execute(select(UserModel).where(UserModel.is_active == True))
        active_users = result.scalars().all()
        
        updated_count = 0
        for user in active_users:
            # Get or create casual leave balance
            balance_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(
                        UserLeaveBalance.user_id == user.id,
                        UserLeaveBalance.leave_type == LeaveTypeEnum.CASUAL
                    )
                )
            )
            balance = balance_result.scalar_one_or_none()
            
            if balance:
                balance.balance = float(balance.balance) + monthly_rate
            else:
                # Create new balance entry
                new_balance = UserLeaveBalance(
                    user_id=user.id,
                    leave_type=LeaveTypeEnum.CASUAL,
                    balance=monthly_rate
                )
                db.add(new_balance)
            updated_count += 1
        
        await db.commit()
        print(f"--- [Scheduler] Accrual Complete. Updated {updated_count} users. ---")
        return None

async def yearly_leave_reset():
    """
    Resets leave balances for all employees on Jan 1st.
    Logic:
    - CL: Reset to 0 (Lapses, new accrual starts).
    - SL: Reset to Policy Quota.
    - WFH: Reset to Policy Quota.
    - EL: Carry forward 50% of current balance.
    """
    print(f"--- [Scheduler] Running Yearly Reset: {datetime.datetime.now()} ---")
    
    async with AsyncSessionLocal() as db:
        current_year = datetime.datetime.now().year
        policy = await get_effective_policy(current_year, db)
        
        sick_quota = float(policy.get("sick_leave_quota", 5))
        wfh_quota = int(policy.get("wfh_quota", 2))
        
        print(f"[Scheduler] Applying Yearly Reset. SL={sick_quota}, WFH={wfh_quota}, CL=Reset(0), EL=50% Carry")

        # Get all users
        result = await db.execute(select(UserModel))
        users = result.scalars().all()
        
        # Process each user's balances
        for user in users:
            # Reset CL, SL, WFH
            for leave_type, balance_value in [
                (LeaveTypeEnum.CASUAL, 0.0),
                (LeaveTypeEnum.SICK, sick_quota),
                (LeaveTypeEnum.WFH, wfh_quota)
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
                
                if balance:
                    balance.balance = balance_value
                else:
                    new_balance = UserLeaveBalance(
                        user_id=user.id,
                        leave_type=leave_type,
                        balance=balance_value
                    )
                    db.add(new_balance)
            
            # Handle Earned Leave (Carry forward 50%)
            el_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(
                        UserLeaveBalance.user_id == user.id,
                        UserLeaveBalance.leave_type == LeaveTypeEnum.EARNED
                    )
                )
            )
            el_balance = el_result.scalar_one_or_none()
            
            if el_balance:
                old_el = float(el_balance.balance)
                new_el = old_el / 2.0
                el_balance.balance = new_el
            else:
                # Create new EL balance with 0 (no carry forward if no previous balance)
                new_el_balance = UserLeaveBalance(
                    user_id=user.id,
                    leave_type=LeaveTypeEnum.EARNED,
                    balance=0.0
                )
                db.add(new_el_balance)
        
        await db.commit()
        print(f"[Scheduler] Yearly Reset processed for {len(users)} users.")
    
    # 3. Trigger Monthly Accrual for the starting month (Jan) or current month (Manual Reset)
    # This fixes the issue where CL is 0 because Accrual ran before Reset or hasn't run yet.
    print("[Scheduler] Triggering post-reset Monthly Accrual...")
    await monthly_accrual()

    print("--- [Scheduler] Yearly Reset Complete ---")
    return None

def start_scheduler():
    # Trigger: 1st day of month at 00:00
    scheduler.add_job(monthly_accrual, 'cron', day=1, hour=0, minute=0)
    
    # Trigger: Jan 1st at 00:05 (slightly after monthly to allow coordination if needed, or simply same time)
    scheduler.add_job(yearly_leave_reset, 'cron', month=1, day=1, hour=0, minute=5)
    
    if not scheduler.running:
        scheduler.start()
        print("--- [Scheduler] Started ---")

def shutdown_scheduler():
    scheduler.shutdown()
    print("--- [Scheduler] Shutdown ---")
