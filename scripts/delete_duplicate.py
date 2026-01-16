import asyncio
from src.db import users_collection
from bson import ObjectId

async def clean_duplicates():
    # ID of the record with Name: "lekha george" but Email: "sonal..."
    # This is clearly the mismatch/error.
    target_id = ObjectId('69660ad92f18cd2b81978534')
    
    print(f"Deleting user with ID: {target_id}")
    res = await users_collection.delete_one({"_id": target_id})
    if res.deleted_count:
        print("Successfully deleted duplicate record.")
    else:
        print("Record not found.")

if __name__ == "__main__":
    asyncio.run(clean_duplicates())
