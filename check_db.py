import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

async def check_db():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]
    admin_collection = db.get_collection("admins")
    
    admins = await admin_collection.find({}).to_list(length=10)
    print("Admins in DB:", admins)
    
    # Check if 'admin' exists
    admin_user = await admin_collection.find_one({"username": "admin"})
    if admin_user:
        print("Admin user found in DB. Password hash:", admin_user.get("password"))
    else:
        print("Admin user NOT found in DB. Fallback should work.")

if __name__ == "__main__":
    asyncio.run(check_db())
