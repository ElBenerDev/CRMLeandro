from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from app.database import DEFAULT_INVENTORY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_inventory():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.crm_leandro
    
    try:
        # Drop existing inventory
        await db.inventory.drop()
        logger.info("Dropped existing inventory collection")
        
        # Create index
        await db.inventory.create_index("name", unique=True)
        logger.info("Created unique index on name field")
        
        # Insert all items
        result = await db.inventory.insert_many(DEFAULT_INVENTORY)
        logger.info(f"✅ Successfully added {len(result.inserted_ids)} inventory items")
        
        # Verify count
        count = await db.inventory.count_documents({})
        logger.info(f"Total items in inventory: {count}")
        
    except Exception as e:
        logger.error(f"❌ Error resetting inventory: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(reset_inventory())