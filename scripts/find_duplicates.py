import asyncio
from src.db import users_collection
from collections import defaultdict

async def find_duplicates():
    print("Scanning for duplicate emails...")
    pipeline = [
        {"$group": {
            "_id": "$email",
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"}
        }},
        {"$match": {
            "count": {"$gt": 1}
        }}
    ]
    
    cursor = users_collection.aggregate(pipeline)
    async for doc in cursor:
        print(f"Duplicate found: {doc['_id']} (Count: {doc['count']})")
        print(f"IDs: {doc['ids']}")
        
        # Details of each
        for uid in doc['ids']:
            user = await users_collection.find_one({"_id": uid})
            print(f" - {uid}: {user.get('full_name')} | Role: {user.get('role')} | Active: {user.get('is_active')}")

if __name__ == "__main__":
    asyncio.run(find_duplicates())
