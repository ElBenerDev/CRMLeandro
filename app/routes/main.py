from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..database import get_db
from ..utils.constants import ROLES  # Add this import
import logging

logger = logging.getLogger(__name__)
web_router = APIRouter()
api_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

async def verify_admin(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return True

async def verify_session(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    return None

@web_router.get("/dashboard", name="main.dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
    })

# Remove this route since it's now in users.py
# @web_router.get("/users")
# async def users_page(request: Request):
#     ...

@web_router.get("/schedule")
async def schedule_page(request: Request):
    logger.debug("Accessing schedule page")
    try:
        db = await get_db()
        schedules = await db.schedules.find().to_list(None)
        
        # Add colors and employee names for the template
        employee_colors = {
            "ONE": "#ea5c8f",
            "MERLIN": "#46bdc6",
            "KEIDY": "#fbc975"
        }
        
        return templates.TemplateResponse(
            "schedule.html",
            {
                "request": request, 
                "schedules": schedules,
                "colors": employee_colors,
                "is_admin": False  # Default to non-admin
            }
        )
    except Exception as e:
        logger.error(f"Schedule error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.get("/daily-cash")
async def daily_cash_page(request: Request):
    logger.debug("Accessing daily cash page")
    try:
        db = await get_db()
        daily_cash = await db.daily_cash.find().sort("date", -1).to_list(None)
        
        total_billing = sum(entry.get("billing", 0) for entry in daily_cash)
        total_expenses = sum(entry.get("expenses", 0) for entry in daily_cash)
        total_balance = total_billing - total_expenses
        
        return templates.TemplateResponse(
            "daily_cash.html",
            {
                "request": request,
                "daily_cash": daily_cash,
                "total_billing": total_billing,
                "total_expenses": total_expenses,
                "total_balance": total_balance,
                "is_admin": False  # Default to non-admin
            }
        )
    except Exception as e:
        logger.error(f"Daily cash error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/status")
async def status():
    return {"status": "ok"}

# Combine routers
router = APIRouter(prefix="/main", tags=["main"])
for route in web_router.routes:
    router.routes.append(route)
for route in api_router.routes:
    router.routes.append(route)