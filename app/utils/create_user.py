from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def create_test_user():
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.crm_leandro
        
        # Test connection
        await db.command("ping")
        logger.info("✅ Connected to MongoDB!")
        
        # Create test user
        test_user = {
            "username": "admin",
            "hashed_password": get_password_hash("admin123"),
            "role": "admin"
        }
        
        # Check if user exists
        existing_user = await db.users.find_one({"username": test_user["username"]})
        if not existing_user:
            await db.users.insert_one(test_user)
            logger.info(f"✅ Created test user: {test_user['username']}")
        else:
            logger.info(f"ℹ️ User {test_user['username']} already exists")

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
    finally:
        client.close()
        logger.info("Closed MongoDB connection")

if __name__ == "__main__":
    asyncio.run(create_test_user())