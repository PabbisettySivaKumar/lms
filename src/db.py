import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "leave_management_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_collection = db["users"]
job_logs_collection = db["job_logs"]


async def get_database():
    return db

async def create_indexes():
    # Users Indexes
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("employee_id", unique=True, sparse=True) # sparse allows nulls if any
    await users_collection.create_index("role")
    
    # Holidays Indexes
    await db["holidays"].create_index("date", unique=True)
    
    # Leave Requests Indexes
    await db["leave_requests"].create_index("applicant_id")
    await db["leave_requests"].create_index("status")
    await db["leave_requests"].create_index("approver_id")
    
    # Comp Off Claims Indexes
    await db["comp_off_claims"].create_index("claimant_id")
    await db["comp_off_claims"].create_index("status")
    
    # Job Logs Indexes
    await job_logs_collection.create_index("job_name")
    await job_logs_collection.create_index([("job_name", 1), ("status", 1)])
