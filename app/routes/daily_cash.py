from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..database import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create two separate routers
web_router = APIRouter()
api_router = APIRouter(prefix="/api/daily-cash", tags=["daily-cash"])

templates = Jinja2Templates(directory="app/templates")

# Web routes
@web_router.get("/daily-cash")
async def daily_cash_page(request: Request):
    logger.debug("Accessing daily cash page")
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    try:
        db = await get_db()
        daily_cash = await db.daily_cash.find().sort("date", -1).to_list(None)
        logger.debug(f"Found {len(daily_cash)} daily cash entries")
        
        return templates.TemplateResponse(
            "daily_cash.html",
            {
                "request": request,
                "daily_cash": daily_cash,
                "user": request.session.get("user")
            }
        )
    except Exception as e:
        logger.error(f"Daily cash page error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API routes
@api_router.get("/")
async def get_daily_cash():
    try:
        db = await get_db()
        daily_cash = await db.daily_cash.find().to_list(None)
        return {"daily_cash": daily_cash}
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Combine routers at the module level
web_router.include_router(api_router)
router = web_router