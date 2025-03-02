from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json

async def verify_schedule_data():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.crm_leandro
    
    schedules = await db.schedules.find().to_list(1000)
    print("\nCurrent schedules in database:")
    print(json.dumps(schedules, indent=2, default=str))
    
    client.close()

if __name__ == "__main__":
    asyncio.run(verify_schedule_data())