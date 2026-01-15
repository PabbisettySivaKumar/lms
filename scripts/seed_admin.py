import asyncio
import sys
import os

# Add the project root to sys.path so we can import from src
sys.path.append(os.getcwd())

from src.db import users_collection
from src.models.user import UserRole
from src.utils.security import get_password_hash

async def seed_admin():
    admin_email = "admin@dotkonnekt.com"
    
    existing_admin = await users_collection.find_one({"email": admin_email})
    if existing_admin:
        print(f"Admin user {admin_email} already exists.")
        return

    admin_data = {
        "employee_id": "ADMIN001",
        "email": admin_email,
        "full_name": "Super Admin",
        "role": UserRole.ADMIN,
        "is_active": True,
        "reset_required": False,
        "hashed_password": get_password_hash("Admin@123"),
        # Default Balances (Can be adjusted)
        "casual_balance": 12.0,
        "sick_balance": 3.0,
        "earned_balance": 0.0,
        "wfh_balance": 2,
        "manager_id": None,
        "manager_name": None
    }
    
    result = await users_collection.insert_one(admin_data)
    print(f"Super Admin created successfully with ID: {result.inserted_id}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_admin())
