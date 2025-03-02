from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    client = None
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.crm_leandro
        
        # Test connection
        await db.command("ping")
        logger.info("✅ Connected to MongoDB!")
        
        # Create admin user
        admin_data = {
            "username": "admin",
            "password": pwd_context.hash("admin123"),  # Hash the password
            "role": "admin"
        }
        
        # Check if admin exists
        existing = await db.users.find_one({"username": "admin"})
        if not existing:
            await db.users.insert_one(admin_data)
            logger.info("✅ Admin user created successfully")
        else:
            await db.users.update_one(
                {"username": "admin"},
                {"$set": admin_data}
            )
            logger.info("✅ Admin user updated successfully")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
    finally:
        if client:
            client.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(create_admin())