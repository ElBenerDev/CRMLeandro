from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import logging
from typing import List
from ..models.schedule import Schedule, Employee, EMPLOYEE_COLORS, DEFAULT_SCHEDULES, default_employees
from ..database import db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DAYS = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]

@router.get("/", response_model=List[Schedule])
async def get_schedules():
    schedules = await db.schedules.find().to_list(1000)
    return [Schedule(**schedule) for schedule in schedules]

@router.post("/")
async def create_schedule(schedule: Schedule):
    schedule_dict = schedule.dict()
    result = await db.schedules.insert_one(schedule_dict)
    return {"id": str(result.inserted_id)}

@router.get("/schedule")
async def schedule_page(request: Request):
    # Your schedule route logic here
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        "schedule.html",
        {
            "request": request,
            "employees": default_employees,
            "days": DAYS,
            "is_admin": request.session.get("is_admin", False)
        }
    )