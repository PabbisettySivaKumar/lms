"""
Script to delete all data from all database tables (truncate).
WARNING: This permanently removes all data. Use only for dev/reset.
Run from project root: python -m scripts.truncate_all_tables
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import backend.models  # noqa: F401 - register all tables with Base
from backend.db import engine, Base, init_db, close_db
from sqlalchemy import text  # type: ignore


async def truncate_all():
    """Disable FK checks, truncate every table, re-enable FK checks."""
    await init_db()
    table_names = list(Base.metadata.tables.keys())
    if not table_names:
        print("No tables found in metadata.")
        await close_db()
        return

    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for name in table_names:
            await conn.execute(text(f"TRUNCATE TABLE `{name}`"))
            print(f"  Truncated: {name}")
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    print(f"✅ Truncated {len(table_names)} tables.")
    await engine.dispose()
    await close_db()


if __name__ == "__main__":
    print("⚠️  This will DELETE all data in all tables.")
    reply = input("Type 'yes' to continue: ").strip().lower()
    if reply != "yes":
        print("Aborted.")
        sys.exit(1)
    asyncio.run(truncate_all())
