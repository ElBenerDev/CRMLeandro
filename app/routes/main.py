from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
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

@router.get("/")
@router.get("/dashboard")
async def dashboard(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    try:
        # Get dashboard statistics
        orders_count = await db.orders.count_documents({})
        recent_orders = await db.orders.find().sort('_id', -1).limit(5).to_list(5)
        users_count = await db.users.count_documents({})
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "orders_count": orders_count,
            "recent_orders": recent_orders,
            "users_count": users_count
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "error": "Error loading dashboard data"
        })

@router.get("/users")
async def users(request: Request, _=Depends(verify_admin)):
    try:
        users_list = await db.users.find().to_list(None)
        return templates.TemplateResponse("users.html", {
            "request": request,
            "users": users_list
        })
    except Exception as e:
        logger.error(f"Users page error: {e}")
        return templates.TemplateResponse("users.html", {
            "request": request,
            "error": "Error loading users data"
        })

@router.get("/inventory")
async def inventory_page(request: Request):
    if session_redirect := await verify_session(request):
        return session_redirect
    try:
        inventory_items = await db.inventory.find().to_list(None)
        return templates.TemplateResponse("inventory.html", {
            "request": request,
            "inventory": inventory_items
        })
    except Exception as e:
        logger.error(f"Inventory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule")
async def schedule_page(request: Request):
    if session_redirect := await verify_session(request):
        return session_redirect
    try:
        schedules = await db.schedules.find().to_list(None)
        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "schedules": schedules
        })
    except Exception as e:
        logger.error(f"Schedule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily-cash")
async def daily_cash_page(request: Request):
    if session_redirect := await verify_session(request):
        return session_redirect
    try:
        daily_cash = await db.daily_cash.find().sort("date", -1).to_list(None)
        return templates.TemplateResponse("daily_cash.html", {
            "request": request,
            "daily_cash": daily_cash
        })
    except Exception as e:
        logger.error(f"Daily cash error: {e}")
        raise HTTPException(status_code=500, detail=str(e))