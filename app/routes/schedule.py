from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import logging
from typing import List
from ..models.schedule import Schedule, Employee, EMPLOYEE_COLORS, DEFAULT_SCHEDULES, default_employees
from ..database import db, get_db

logger = logging.getLogger(__name__)

# Create two separate routers like inventory
web_router = APIRouter()
api_router = APIRouter(prefix="/api/schedule", tags=["schedule"])

templates = Jinja2Templates(directory="app/templates")

DAYS = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]

# Move web routes to web_router
@web_router.get("/schedule")
async def schedule_page(request: Request):
    logger.debug("Accessing schedule page")
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    try:
        db = await get_db()
        schedules = await db.schedules.find().to_list(None)
        logger.debug(f"Found {len(schedules)} schedule entries")
        return templates.TemplateResponse(
            "schedule.html",
            {
                "request": request,
                "schedules": schedules,
                "user": request.session.get("user")
            }
        )
    except Exception as e:
        logger.error(f"Schedule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Move API routes to api_router
@api_router.get("/", response_model=List[Schedule])
async def get_schedules():
    schedules = await db.schedules.find().to_list(1000)
    return [Schedule(**schedule) for schedule in schedules]

@api_router.post("/")
async def create_schedule(schedule: Schedule):
    schedule_dict = schedule.dict()
    result = await db.schedules.insert_one(schedule_dict)
    return {"id": str(result.inserted_id)}

# Combine routers
web_router.include_router(api_router)
router = web_router