from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime  # Add this import
import os
import asyncio
import logging
import bcrypt  # Add this import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
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
        
        # Create admin user with current timestamp
        admin_data = {
            "username": "admin",
            "password": pwd_context.hash("admin123"),
            "is_admin": True,
            "active": True,
            "created_at": datetime.utcnow()  # Use UTC time
        }
        
        # Create users collection if it doesn't exist
        collections = await db.list_collection_names()
        if "users" not in collections:
            await db.create_collection("users")
            await db.users.create_index("username", unique=True)
            logger.info("✅ Users collection created")
        
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
        raise
    finally:
        if client:
            client.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(create_admin())