from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user():
    client = None
    try:
        # Load MongoDB Atlas connection string
        load_dotenv()
        uri = os.getenv("MONGODB_URL")
        if not uri:
            raise Exception("MONGODB_URL not found in environment variables")

        # Connect to MongoDB Atlas
        client = AsyncIOMotorClient(
            uri,
            server_api=ServerApi('1'),
            serverSelectionTimeoutMS=5000
        )
        db = client.crm_leandro
        
        # Test connection
        await db.command("ping")
        logger.info("✅ Connected to MongoDB Atlas!")
        
        # Create regular user with current timestamp
        user_data = {
            "username": "user",
            "password": pwd_context.hash("user123"),
            "is_admin": False,
            "permissions": ["view_inventory"],
            "active": True,
            "created_at": datetime.utcnow()
        }
        
        # Check if user exists
        existing = await db.users.find_one({"username": "user"})
        if not existing:
            await db.users.insert_one(user_data)
            logger.info("✅ Regular user created successfully")
        else:
            await db.users.update_one(
                {"username": "user"},
                {"$set": user_data}
            )
            logger.info("✅ Regular user updated successfully")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise
    finally:
        if client:
            client.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(create_user())