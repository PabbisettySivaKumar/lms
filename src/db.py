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
