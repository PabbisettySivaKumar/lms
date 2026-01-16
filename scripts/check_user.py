import asyncio
from src.db import users_collection

async def check_sonal():
    email = "sonal.sasidharan@dotkonnekt.com"
    count = await users_collection.count_documents({"email": email})
    print(f"Count for {email}: {count}")

if __name__ == "__main__":
    asyncio.run(check_sonal())
