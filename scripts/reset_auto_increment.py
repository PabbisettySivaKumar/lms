"""
Script to reset AUTO_INCREMENT for the users table.
WARNING: This only resets the counter for NEW rows, it does NOT renumber existing rows.
Renumbering existing rows is dangerous and can break foreign key relationships.
"""
import asyncio
from backend.db import execute_query, get_connection

async def reset_users_auto_increment():
    """
    Reset AUTO_INCREMENT to the next available ID.
    This ensures the next new user gets the lowest available ID.
    """
    # Get the maximum ID currently in use
    result = await execute_query("SELECT MAX(id) as max_id FROM users")
    max_id = result[0].get("max_id", 0) if result else 0
    
    # Set AUTO_INCREMENT to max_id + 1
    next_id = max_id + 1
    query = f"ALTER TABLE users AUTO_INCREMENT = {next_id}"
    
    # ALTER TABLE needs a direct connection
    async with get_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query)
    
    print(f"✅ AUTO_INCREMENT reset to {next_id}")
    print(f"   Next new user will get ID: {next_id}")
    print(f"   Current max ID in table: {max_id}")

if __name__ == "__main__":
    asyncio.run(reset_users_auto_increment())
