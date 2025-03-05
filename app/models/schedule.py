from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import time

class DaySchedule(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_off: bool = False

class Schedule(BaseModel):
    employee: str
    day: str
    start_time: Optional[str]
    end_time: Optional[str]
    is_off: bool = False

class Employee(BaseModel):
    name: str
    color: str
    schedule: Dict[str, DaySchedule]

# Define default schedules
EMPLOYEE_COLORS = {
    "ONE": "#ea5c8f",
    "MERLIN": "#46bdc6",
    "KEIDY": "#fbc975"
}

# Helper function to create DaySchedule
def create_schedule(time_range: str = None, is_off: bool = False) -> DaySchedule:
    if is_off:
        return DaySchedule(is_off=True)
    if time_range:
        start, end = time_range.replace(" a ", " ").split(" ")
        return DaySchedule(start_time=start, end_time=end)
    return DaySchedule(is_off=True)

# Add DEFAULT_SCHEDULES constant
DEFAULT_SCHEDULES = {
    "LUNES": ["7:00", "12:00"],
    "MARTES": ["7:00", "12:00"],
    "MIERCOLES": ["7:00", "12:00"],
    "JUEVES": ["7:00", "12:00"],
    "VIERNES": ["7:00", "12:00"],
    "SABADO": ["7:00", "12:00"],
    "DOMINGO": ["7:00", "12:00"]
}

# Default schedules for each employee
default_employees = [
    Employee(
        name="ONE",
        color=EMPLOYEE_COLORS["ONE"],
        schedule={
            "LUNES": create_schedule(is_off=True),
            "MARTES": create_schedule("7:00 a 12:00"),
            "MIERCOLES": create_schedule("4:00 a 12:00"),
            "JUEVES": create_schedule("3:00 a 12:00"),
            "VIERNES": create_schedule("6:00 a 12:00"),
            "SABADO": create_schedule("3:00 a 12:00"),
            "DOMINGO": create_schedule("6:00 a 10:00")
        }
    ),
    Employee(
        name="MERLIN",
        color=EMPLOYEE_COLORS["MERLIN"],
        schedule={
            "LUNES": create_schedule("4:00 a 12:00"),
            "MARTES": create_schedule(is_off=True),
            "MIERCOLES": create_schedule("7:00 a 12:00"),
            "JUEVES": create_schedule(is_off=True),
            "VIERNES": create_schedule("7:00 a 12:00"),
            "SABADO": create_schedule("7:00 a 12:00"),
            "DOMINGO": create_schedule("7:00 a 12:00")
        }
    ),
    Employee(
        name="KEIDY",
        color=EMPLOYEE_COLORS["KEIDY"],
        schedule={
            "LUNES": create_schedule("7:00 a 12:00"),
            "MARTES": create_schedule("4:00 a 12:00"),
            "MIERCOLES": create_schedule(is_off=True),
            "JUEVES": create_schedule("6:00 a 12:00"),
            "VIERNES": create_schedule("3:00 a 10:00"),
            "SABADO": create_schedule("6:00 a 12:00"),
            "DOMINGO": create_schedule("3:00 a 10:00")
        }
    )
]