"""
Script to seed default roles and role-scope mappings
"""
import asyncio
import sys
import os
from sqlalchemy import select  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.db import AsyncSessionLocal
from backend.models import Role, RoleScope
from backend.utils.scopes import Scope, ROLE_SCOPES
from backend.models.user import UserRole as UserRoleEnum

async def seed_roles():
    """Seed default roles and their scopes"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if roles already exist
            result = await session.execute(select(Role))
            existing_roles = result.scalars().all()
            
            # Create roles map from existing or new roles
            roles_map = {}
            
            if existing_roles:
                print("📋 Roles already exist. Using existing roles.")
                for role in existing_roles:
                    roles_map[role.name] = role
            else:
                print("📝 Creating new roles...")
                # Create roles
                for role_enum in UserRoleEnum:
                    role = Role(
                        name=role_enum.value,
                        display_name=role_enum.value.title(),
                        description=f"{role_enum.value.title()} role",
                        is_active=True
                    )
                    session.add(role)
                    roles_map[role_enum.value] = role
                await session.flush()  # Get IDs
            
            # Check if scopes already exist
            result = await session.execute(select(RoleScope))
            existing_scopes = result.scalars().all()
            existing_scope_set = {(rs.role_id, rs.scope_name) for rs in existing_scopes}
            
            # Create role-scope mappings (only add missing ones)
            added_count = 0
            for role_name, scopes in ROLE_SCOPES.items():
                if role_name not in roles_map:
                    print(f"⚠️  Role '{role_name}' not found in database. Skipping scopes for this role.")
                    continue
                    
                role = roles_map[role_name]
                for scope in scopes:
                    if (role.id, scope) not in existing_scope_set:
                        role_scope = RoleScope(
                            role_id=role.id,
                            scope_name=scope
                        )
                        session.add(role_scope)
                        added_count += 1
            
            if added_count > 0:
                await session.commit()
                print(f"✅ Added {added_count} new role-scope mappings!")
            else:
                print("✅ All role-scope mappings already exist.")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding roles: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_roles())
