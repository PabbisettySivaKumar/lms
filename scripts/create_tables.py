"""
Script to create database tables using SQLAlchemy
Run this once to initialize the database schema
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.db import init_db, engine, Base
from backend.models import (
    User, Role, RoleScope, UserRole, UserLeaveBalance, UserBalanceHistory,
    UserDocument, LeaveRequest, CompOffClaim, Holiday, Policy, PolicyDocument,
    PolicyAcknowledgment, JobLog, Notification, LeaveComment, LeaveAttachment,
    AuditLog
)

async def create_tables():
    """Create all database tables"""
    print("🔄 Creating database tables...")
    try:
        await init_db()
        print("Database tables created successfully!")
        print("\nTables created:")
        print("  - users")
        print("  - roles")
        print("  - role_scopes")
        print("  - user_roles")
        print("  - user_leave_balances")
        print("  - user_balance_history")
        print("  - user_documents")
        print("  - leave_requests")
        print("  - comp_off_claims")
        print("  - holidays")
        print("  - policies")
        print("  - policy_documents")
        print("  - policy_acknowledgments")
        print("  - job_logs")
        print("  - notifications")
        print("  - leave_comments")
        print("  - leave_attachments")
        print("  - audit_logs")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
