from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
load_dotenv()

async def init_cash_register_collections():
    MONGODB_URL = os.getenv("MONGODB_URL")
    if not MONGODB_URL:
        raise ValueError("MONGODB_URL environment variable is not set")

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.crm_leandro

    try:
        # Create cash register indexes
        await db.cash_register.create_index([
            ("date", -1),
            ("status", 1)
        ])
        await db.cash_register.create_index([
            ("responsible", 1),
            ("status", 1)
        ])

        # Create cash transactions index
        await db.cash_transactions.create_index([
            ("cash_register_id", 1),
            ("time", 1)
        ])

        # Set up schema validation
        await db.command({
            'collMod': 'cash_register',
            'validator': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['date', 'initial_amount', 'responsible', 'status'],
                    'properties': {
                        'date': {'bsonType': 'date'},
                        'initial_amount': {'bsonType': 'double'},
                        'initial_amount_verified': {'bsonType': 'bool'},
                        'status': {'enum': ['open', 'closed']},
                        'responsible': {'bsonType': 'string'}
                    }
                }
            }
        })

        logger.info("Cash register collections initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing cash register collections: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_cash_register_collections())