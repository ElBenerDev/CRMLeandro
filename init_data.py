from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import asyncio

async def init_daily_cash():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.crm_leandro
    
    # Sample daily cash entry from the template
    sample_entry = {
        "date": datetime(2025, 3, 1),
        "initial_amount": 200.00,
        "billing": 1000.00,
        "expenses": 100.00,
        "details": "",
        "safe_amount": 900.00,
        "responsible": "ONE"
    }
    
    await db.daily_cash.insert_one(sample_entry)

async def init_schedules():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.crm_leandro
    
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
                "SABADO": {"start_time": "3:00", "end_time": "10:00"},
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
        },
        {
            "name": "KEIDY",
            "color": "#fbc975",
            "schedule": {
                "LUNES": {"start_time": "7:00", "end_time": "12:00"},
                "MARTES": {"start_time": "4:00", "end_time": "12:00"},
                "MIERCOLES": {"is_off": True},
                "JUEVES": {"start_time": "6:00", "end_time": "12:00"},
                "VIERNES": {"start_time": "3:00", "end_time": "10:00"},
                "SABADO": {"start_time": "6:00", "end_time": "12:00"},
                "DOMINGO": {"start_time": "3:00", "end_time": "10:00"}
            }
        }
    ]
    
    await db.schedules.insert_many(schedules)

async def main():
    await init_daily_cash()
    await init_schedules()
    print("Data initialized successfully")

if __name__ == "__main__":
    asyncio.run(main())