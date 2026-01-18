from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.db import users_collection, db
import datetime

scheduler = AsyncIOScheduler()

async def get_effective_policy(year: int):
    """
    Fetches policy for the given year. 
    If not found, falls back to the most recent previous year (Continuity).
    Defaults if no policies exist at all.
    """
    policies_collection = db.policies
    
    # 1. Try Specific Year
    policy = await policies_collection.find_one({"year": year})
    if policy:
        print(f"[Policy] Using defined policy for {year}")
        return policy
        
    # 2. Fallback to Latest Previous Year
    # Find one policy with year < given_year, sorted descending
    fallback = await policies_collection.find_one({"year": {"$lt": year}}, sort=[("year", -1)])
    if fallback:
        print(f"[Policy] No policy for {year}. Continuing with {fallback['year']} policy.")
        return fallback
        
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
    
    current_year = datetime.datetime.now().year
    policy = await get_effective_policy(current_year)
    
    casual_quota = policy.get("casual_leave_quota", 12)
    monthly_rate = round(casual_quota / 12, 2)
    
    print(f"[Scheduler] Accruing {monthly_rate} CL (Quota: {casual_quota})")
    
    result = await users_collection.update_many(
        {"is_active": True},
        {"$inc": {"casual_balance": monthly_rate}}
    )
    
    print(f"--- [Scheduler] Accrual Complete. Updated {result.modified_count} users. ---")

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
    
    current_year = datetime.datetime.now().year
    policy = await get_effective_policy(current_year)
    
    sick_quota = float(policy.get("sick_leave_quota", 5))
    wfh_quota = int(policy.get("wfh_quota", 2))
    
    print(f"[Scheduler] Applying Yearly Reset. SL={sick_quota}, WFH={wfh_quota}, CL=Reset(0), EL=50% Carry")

    # 1. Reset CL, SL, WFH via Bulk Update (Efficient)
    await users_collection.update_many(
        {},
        {"$set": {
            "casual_balance": 0.0,
            "sick_balance": sick_quota,
            "wfh_balance": wfh_quota
        }}
    )
    
    # 2. Handle Earned Leave (Requires calculation per user)
    # We can use an aggregation pipeline or bulk writes. Bulk writes are safer for logic.
    from pymongo import UpdateOne
    
    operations = []
    async for user in users_collection.find({}, {"_id": 1, "earned_balance": 1}):
        old_el = user.get("earned_balance", 0.0)
        new_el = old_el / 2.0
        
        operations.append(
            UpdateOne({"_id": user["_id"]}, {"$set": {"earned_balance": new_el}})
        )
        
    if operations:
        await users_collection.bulk_write(operations)
        print(f"[Scheduler] EL Carry Forward processed for {len(operations)} users.")
    
    # 3. Trigger Monthly Accrual for the starting month (Jan) or current month (Manual Reset)
    # This fixes the issue where CL is 0 because Accrual ran before Reset or hasn't run yet.
    print("[Scheduler] Triggering post-reset Monthly Accrual...")
    await monthly_accrual()

    print("--- [Scheduler] Yearly Reset Complete ---")

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
