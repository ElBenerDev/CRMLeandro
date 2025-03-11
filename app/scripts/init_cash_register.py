import logging
from datetime import datetime
from ..database import get_db

logger = logging.getLogger(__name__)

DEFAULT_CASH_REGISTER = {
    "date": datetime.now(),
    "initial_amount": 200.00,
    "transactions": [],
    "billing": 0,
    "expenses": 0,
    "final_amount": 200.00,  # Starts equal to initial_amount
    "responsible": "admin",
    "status": "closed"
}

async def init_cash_register():
    try:
        db = await get_db()
        
        # Check if collection exists and is empty
        if await db.cash_register.count_documents({}) == 0:
            default_entry = {
                "date": datetime.now(),
                "initial_amount": 200.00,
                "billing": 0,
                "expenses": 0,
                "final_amount": 200.00,
                "responsible": "admin",
                "status": "closed"
            }
            
            await db.cash_register.insert_one(default_entry)
            logger.info("Cash register initialized with default entry")
            
        return True
    except Exception as e:
        logger.error(f"Error initializing cash register: {e}")
        return False