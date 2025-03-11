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
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    try:
        logger.debug("Fetching daily cash data")
        db = await get_db()
        
        # Get daily cash entries with all fields
        daily_cash = await db.cash_register.find(
            {"status": "closed"}
        ).sort("date", -1).to_list(None)
        
        logger.debug(f"Found {len(daily_cash)} entries")

        # Calculate totals
        total_initial = sum(entry.get("initial_amount", 0) for entry in daily_cash)
        total_billing = sum(entry.get("billing", 0) for entry in daily_cash)
        total_expenses = sum(entry.get("expenses", 0) for entry in daily_cash)
        total_balance = sum(entry.get("final_amount", 0) for entry in daily_cash)

        logger.debug(f"Totals calculated: initial={total_initial}, billing={total_billing}, expenses={total_expenses}")

        return templates.TemplateResponse(
            "daily_cash.html",
            {
                "request": request,
                "daily_cash": daily_cash,
                "total_initial": total_initial,
                "total_billing": total_billing,
                "total_expenses": total_expenses,
                "total_balance": total_balance,
                "error": None
            }
        )
    except Exception as e:
        logger.error(f"Daily cash error: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "daily_cash.html",
            {
                "request": request,
                "daily_cash": [],
                "total_initial": 0,
                "total_billing": 0,
                "total_expenses": 0,
                "total_balance": 0,
                "error": str(e)
            }
        )

# API routes
@api_router.get("/")
async def get_daily_cash():
    try:
        db = await get_db()
        daily_cash = await db.cash_register.find({"status": "closed"}).to_list(None)
        return {"daily_cash": daily_cash}
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Combine routers at the module level
web_router.include_router(api_router)
router = web_router