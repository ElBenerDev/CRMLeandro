import asyncio
from app.database import init_db
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection():
    # Verify environment variables
    load_dotenv()
    mongo_url = os.getenv("MONGODB_URL")
    if not mongo_url:
        logger.error("MONGODB_URL not found in .env file")
        return
    
    # Mask password in logs
    safe_url = mongo_url.replace(
        mongo_url.split('@')[0].split(':')[2],
        '*' * 8
    )
    logger.debug(f"Attempting connection to: {safe_url}")
    
    if await init_db():
        logger.info("Database connection successful!")
    else:
        logger.error("Failed to connect to database")

if __name__ == "__main__":
    asyncio.run(test_connection())