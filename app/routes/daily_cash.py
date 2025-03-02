from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..models.daily_cash import default_cash_entry
from ..database import db
from datetime import datetime, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/daily-cash")
async def daily_cash_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    
    # Generate a month of entries
    start_date = datetime(2025, 3, 1)
    entries = []
    for i in range(31):
        entry = default_cash_entry.copy()
        entry["date"] = (start_date + timedelta(days=i)).strftime("%d/%m/%Y")
        entries.append(entry)
    
    return templates.TemplateResponse(
        "daily_cash.html",
        {
            "request": request,
            "entries": entries,
            "is_admin": request.session.get("is_admin", False)
        }
    )