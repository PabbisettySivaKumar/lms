import asyncio
import sys
import os
from datetime import date

# Add the project root to sys.path so we can import from src
sys.path.append(os.getcwd())

from backend.db import AsyncSessionLocal, init_db, close_db, get_db
from backend.models import User as UserModel, Role, UserRole, UserLeaveBalance, LeaveTypeEnum
from backend.utils.security import get_password_hash
from sqlalchemy import select  # type: ignore

async def seed_admin():
    """Seed admin user for MySQL database."""
    try:
        # Initialize database connection
        await init_db()
        print("✅ Database connection initialized")
        
        admin_email = "admin@dotkonnekt.com"
        
        async with AsyncSessionLocal() as db:
            # Check if admin already exists
            result = await db.execute(select(UserModel).where(UserModel.email == admin_email))
            existing_admin = result.scalar_one_or_none()
            if existing_admin:
                print(f"✅ Admin user {admin_email} already exists.")
                return
            
            # Step 1: Insert user into users table
            print("🔄 Creating admin user...")
            admin_user = UserModel(
                employee_id="ADMIN001",
                email=admin_email,
                full_name="Super Admin",
                hashed_password=get_password_hash("Admin@123"),
                is_active=True,
                reset_required=False,
                joining_date=date.today(),
                manager_id=None,
            )
            db.add(admin_user)
            await db.flush()  # Flush to get the ID
            user_id = admin_user.id
            print(f"✅ User created with ID: {user_id}")
            
            # Step 2: Find or create admin role
            print("🔄 Assigning admin role...")
            result = await db.execute(select(Role).where(Role.name == "admin"))
            admin_role = result.scalar_one_or_none()
            
            if not admin_role:
                # Create admin role if it doesn't exist
                admin_role = Role(
                    name="admin",
                    display_name="Administrator",
                    description="Full system access",
                    is_active=True
                )
                db.add(admin_role)
                await db.flush()  # Flush to get the ID
                print(f"✅ Admin role created with ID: {admin_role.id}")
            else:
                print(f"✅ Found admin role with ID: {admin_role.id}")
            
            role_id = admin_role.id
            
            # Step 3: Assign role to user
            result = await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                    UserRole.is_active == True
                )
            )
            existing_user_role = result.scalar_one_or_none()
            
            if not existing_user_role:
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    is_active=True,
                    assigned_by=None  # System assignment
                )
                db.add(user_role)
                print(f"✅ Admin role assigned to user")
            else:
                print(f"✅ User already has admin role")
            
            # Step 4: Set leave balances
            print("🔄 Setting leave balances...")
            
            balances = [
                (LeaveTypeEnum.CASUAL, 12.0),
                (LeaveTypeEnum.SICK, 3.0),
                (LeaveTypeEnum.EARNED, 0.0),
                (LeaveTypeEnum.WFH, 2.0),
                (LeaveTypeEnum.COMP_OFF, 0.0),
            ]
            
            for leave_type, balance_value in balances:
                result = await db.execute(
                    select(UserLeaveBalance).where(
                        UserLeaveBalance.user_id == user_id,
                        UserLeaveBalance.leave_type == leave_type
                    )
                )
                existing_balance = result.scalar_one_or_none()
                
                if not existing_balance:
                    balance = UserLeaveBalance(
                        user_id=user_id,
                        leave_type=leave_type,
                        balance=balance_value
                    )
                    db.add(balance)
                    print(f"   ✅ {leave_type.value}: {balance_value}")
                else:
                    print(f"   ⚠️  {leave_type.value} balance already exists")
            
            await db.commit()
        
        print(f"\n🎉 Super Admin created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Password: Admin@123")
        print(f"   Employee ID: ADMIN001")
        
    except Exception as e:
        print(f"❌ Error seeding admin: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_db()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_admin())
