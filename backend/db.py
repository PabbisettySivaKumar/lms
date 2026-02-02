"""
Database configuration and session management
Combines SQLAlchemy ORM (primary) with legacy aiomysql support (for migration)
"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List, Tuple
import logging

# SQLAlchemy imports
from sqlalchemy import text  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker  # type: ignore
from sqlalchemy.orm import declarative_base  # type: ignore

# Legacy aiomysql imports (for backward compatibility)
import aiomysql  # type: ignore

load_dotenv()

# Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "adminadmin")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "leave_management_db")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")

logger = logging.getLogger(__name__)

# SQLAlchemy Setup (Primary - Recommended)
# SQLAlchemy database URL
DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


# SQLAlchemy dependency for FastAPI
async def get_db() -> AsyncSession:
    """
    Get SQLAlchemy database session (FastAPI dependency).
    Use this in your route handlers.
    
    Example:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ensure_database_exists():
    """
    Create the application database if it does not exist.
    Connects to MySQL server (using 'mysql' system db) and runs CREATE DATABASE IF NOT EXISTS.
    Call this before init_db() when the database might not exist yet (e.g. first-time bootstrap).
    """
    # Connect without our app database so we can create it (use 'mysql' system database)
    url_no_db = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/mysql?charset={MYSQL_CHARSET}"
    temp_engine = create_async_engine(url_no_db, pool_pre_ping=True)
    escaped = MYSQL_DATABASE.replace("`", "``")
    async with temp_engine.begin() as conn:
        await conn.execute(
            text("CREATE DATABASE IF NOT EXISTS `{:s}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(escaped))
        )
    await temp_engine.dispose()
    logger.info(f"Database {MYSQL_DATABASE} ensured (created if missing).")


async def init_db():
    """
    Initialize database - create all tables using SQLAlchemy models.
    This is called on application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"Database initialized: {MYSQL_DATABASE}")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")



# Legacy connection pool
_pool: Optional[aiomysql.Pool] = None


async def get_pool() -> aiomysql.Pool:
    """Get or create MySQL connection pool (legacy - use SQLAlchemy instead)."""
    global _pool
    if _pool is None:
        try:
            _pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DATABASE,
                charset=MYSQL_CHARSET,
                autocommit=True,
                minsize=1,
                maxsize=10,
                cursorclass=aiomysql.DictCursor
            )
            logger.info(f"Legacy MySQL connection pool created for {MYSQL_DATABASE}")
        except Exception as e:
            logger.error(f"Failed to create MySQL connection pool: {str(e)}")
            raise
    return _pool


async def close_pool():
    """Close MySQL connection pool (legacy)."""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("Legacy MySQL connection pool closed")


@asynccontextmanager
async def get_connection():
    """Get a database connection from the pool (legacy - use get_db() instead)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def get_cursor():
    """Get a database cursor from the pool (legacy - use get_db() instead)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                yield cursor
    except Exception as e:
        logger.error(f"Failed to get database cursor: {str(e)}")
        raise

async def execute_query(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries (legacy).
    Use SQLAlchemy select() instead.
    """
    async with get_cursor() as cursor:
        await cursor.execute(query, params)
        return await cursor.fetchall()
