from pydantic import BaseModel
from typing import Dict, List

class DaySchedule(BaseModel):
    start_time: str
    end_time: str

class Employee(BaseModel):
    name: str
    color: str
    schedule: Dict[str, str]

class Schedule(BaseModel):
    employee: str
    weekly_schedule: Dict[str, str]

EMPLOYEE_COLORS = {
    "ONE": "#ea5c8f",
    "MERLIN": "#46bdc6",
    "KEIDY": "#fbc975"
}

DEFAULT_SCHEDULES = {
    "ONE": {
        "LUNES": "OFF",
        "MARTES": "7:00 a 12:00",
        "MIERCOLES": "4:00 a 12:00",
        "JUEVES": "3:00 a 12:00",
        "VIERNES": "6:00 a 12:00",
        "SABADO": "3:00 a 12:00",
        "DOMINGO": "6:00 a 10:00"
    },
    "MERLIN": {
        "LUNES": "4:00 a 12:00",
        "MARTES": "OFF",
        "MIERCOLES": "7:00 a 12:00",
        "JUEVES": "OFF",
        "VIERNES": "7:00 a 12:00",
        "SABADO": "7:00 a 12:00",
        "DOMINGO": "7:00 a 12:00"
    },
    "KEIDY": {
        "LUNES": "7:00 a 12:00",
        "MARTES": "4:00 a 12:00",
        "MIERCOLES": "OFF",
        "JUEVES": "6:00 a 12:00",
        "VIERNES": "3:00 a 10:00",
        "SABADO": "6:00 a 12:00",
        "DOMINGO": "3:00 a 10:00"
    }
}

default_employees = [
    Employee(
        name=name,
        color=EMPLOYEE_COLORS[name],
        schedule=DEFAULT_SCHEDULES[name]
    )
    for name in EMPLOYEE_COLORS.keys()
]