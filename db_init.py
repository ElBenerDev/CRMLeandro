from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.crm_leandro
        
        # Test connection
        await db.command("ping")
        logger.info("✅ Connected to MongoDB!")
        
        # Check if admin exists
        admin = await db.users.find_one({"username": "admin"})
        if not admin:
            # Create admin user
            hashed_password = bcrypt.hash("adminpassword")
            await db.users.insert_one({
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "hashed_password": hashed_password
            })
            logger.info("✅ Admin user created")
        else:
            logger.info("ℹ️ Admin user already exists")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_database())