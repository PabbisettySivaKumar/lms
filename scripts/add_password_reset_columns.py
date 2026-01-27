"""
Script to add password_reset_token and password_reset_expiry columns to users table
"""
import asyncio
import os
from dotenv import load_dotenv
import aiomysql  # type: ignore

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "lms_db")


async def add_password_reset_columns():
    """Add password_reset_token and password_reset_expiry columns to users table"""
    try:
        conn = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset='utf8mb4'
        )
        
        async with conn.cursor() as cursor:
            # Check if columns already exist
            await cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = '{MYSQL_DATABASE}' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME IN ('password_reset_token', 'password_reset_expiry')
            """)
            result = await cursor.fetchone()
            existing_count = result[0] if result else 0
            
            if existing_count == 2:
                print("✅ Columns 'password_reset_token' and 'password_reset_expiry' already exist")
                return
            
            # Add password_reset_token column if it doesn't exist
            if existing_count == 0 or (existing_count == 1 and 'password_reset_token' not in [col[0] for col in await cursor.execute("SHOW COLUMNS FROM users LIKE 'password_reset_token'")]):
                await cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN password_reset_token VARCHAR(255) NULL 
                    COMMENT 'Password reset token'
                """)
                print("✅ Added 'password_reset_token' column")
            
            # Add password_reset_expiry column if it doesn't exist
            if existing_count == 0 or (existing_count == 1 and 'password_reset_expiry' not in [col[0] for col in await cursor.execute("SHOW COLUMNS FROM users LIKE 'password_reset_expiry'")]):
                await cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN password_reset_expiry DATETIME NULL 
                    COMMENT 'Password reset token expiry'
                """)
                print("✅ Added 'password_reset_expiry' column")
            
            await conn.commit()
            print("✅ Successfully added password reset columns to users table")
            
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    asyncio.run(add_password_reset_columns())
