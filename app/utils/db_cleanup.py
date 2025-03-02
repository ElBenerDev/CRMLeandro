from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import logging

async def cleanup_database():
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.crm_leandro
        
        # Remove invalid entries
        result = await db.schedules.delete_many({"employee": None})
        logging.info(f"Removed {result.deleted_count} invalid entries")
        
        client.close()
        return result.deleted_count
    except Exception as e:
        logging.error(f"Database cleanup failed: {e}")
        return 0

if __name__ == "__main__":
    asyncio.run(cleanup_database())