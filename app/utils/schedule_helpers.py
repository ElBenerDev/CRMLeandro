from datetime import datetime, time
from typing import List
from ..models.schedule import Schedule
from ..database import db

async def get_employee_schedule(employee: str, start_date: datetime, end_date: datetime) -> List[Schedule]:
    schedules = await db.schedules.find({
        "employee": employee,
        "date": {
            "$gte": start_date,
            "$lte": end_date
        }
    }).to_list(1000)
    return [Schedule(**schedule) for schedule in schedules]

async def calculate_attendance_stats(employee: str, month: int, year: int) -> dict:
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    schedules = await db.schedules.find({
        "employee": employee,
        "date": {
            "$gte": start_date,
            "$lt": end_date
        }
    }).to_list(1000)
    
    stats = {
        "total": len(schedules),
        "on_time": 0,
        "late": 0,
        "absent": 0
    }
    
    for schedule in schedules:
        stats[schedule["status"].lower().replace(" ", "_")] += 1
    
    return stats