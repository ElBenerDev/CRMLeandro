import asyncio
from app.database import init_db, get_db
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def create_test_data():
    try:
        # Initialize database
        await init_db()
        db = await get_db()

        # Test schedules
        schedules = [
            {
                "name": "ONE",
                "color": "#ea5c8f",
                "schedule": {
                    "LUNES": {"is_off": True},
                    "MARTES": {"start_time": "7:00", "end_time": "12:00"},
                    "MIERCOLES": {"start_time": "4:00", "end_time": "12:00"},
                    "JUEVES": {"start_time": "3:00", "end_time": "12:00"},
                    "VIERNES": {"start_time": "6:00", "end_time": "12:00"},
                    "SABADO": {"start_time": "3:00", "end_time": "12:00"},
                    "DOMINGO": {"start_time": "6:00", "end_time": "10:00"}
                }
            },
            {
                "name": "MERLIN",
                "color": "#46bdc6",
                "schedule": {
                    "LUNES": {"start_time": "4:00", "end_time": "12:00"},
                    "MARTES": {"is_off": True},
                    "MIERCOLES": {"start_time": "7:00", "end_time": "12:00"},
                    "JUEVES": {"is_off": True},
                    "VIERNES": {"start_time": "7:00", "end_time": "12:00"},
                    "SABADO": {"start_time": "7:00", "end_time": "12:00"},
                    "DOMINGO": {"start_time": "7:00", "end_time": "12:00"}
                }
            }
        ]

        for schedule in schedules:
            result = await db.schedules.insert_one(schedule)
            logger.info(f"Added schedule for {schedule['name']} with id: {result.inserted_id}")

        # Test daily cash entries
        daily_cash_entries = [
            {
                "date": datetime.now(),
                "initial_amount": 200.00,
                "billing": 1000.00,
                "expenses": 100.00,
                "details": "Test entry 1",
                "safe_amount": 900.00,
                "responsible": "ONE"
            },
            {
                "date": datetime.now(),
                "initial_amount": 200.00,
                "billing": 800.00,
                "expenses": 50.00,
                "details": "Test entry 2",
                "safe_amount": 750.00,
                "responsible": "MERLIN"
            }
        ]

        for entry in daily_cash_entries:
            result = await db.daily_cash.insert_one(entry)
            logger.info(f"Added daily cash entry with id: {result.inserted_id}")

        logger.info("Test data initialization complete")

    except Exception as e:
        logger.error(f"Error creating test data: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_test_data())