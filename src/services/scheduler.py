from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.db import users_collection
import datetime

scheduler = AsyncIOScheduler()

async def monthly_accrual():
    """
    Adds 1.0 Casual Leave and 0.25 Sick Leave to all active employees.
    Runs on the 1st of every month.
    """
    print(f"--- [Scheduler] Running Monthly Accrual: {datetime.datetime.now()} ---")
    
    result = await users_collection.update_many(
        {"is_active": True},
        {"$inc": {"casual_balance": 1.0, "sick_balance": 0.25}}
    )
    
    print(f"--- [Scheduler] Accrual Complete. Updated {result.modified_count} users. ---")

def start_scheduler():
    # Trigger: 1st day of month at 00:00
    scheduler.add_job(monthly_accrual, 'cron', day=1, hour=0, minute=0)
    scheduler.start()
    print("--- [Scheduler] Started ---")

def shutdown_scheduler():
    scheduler.shutdown()
    print("--- [Scheduler] Shutdown ---")
