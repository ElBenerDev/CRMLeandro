from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import List, Optional
from datetime import datetime, date
from bson import ObjectId
from fastapi.templating import Jinja2Templates
from ..models.cash_register import CashRegister, CashEntry
from ..database import get_db
import logging

logger = logging.getLogger(__name__)

web_router = APIRouter()
api_router = APIRouter(prefix="/api/cash-register", tags=["cash_register"])
templates = Jinja2Templates(directory="app/templates")

@web_router.get("/cash-register", name="cash_register.index")
async def cash_register_page(request: Request):
    try:
        db = await get_db()
        # Get token from cookie
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login", status_code=303)
            
        # Verify token and get user info
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data:
            return RedirectResponse(url="/login", status_code=303)

        # Get cash register entries
        entries = await db.cash_register.find().sort("date", -1).to_list(100)
        return templates.TemplateResponse(
            "cash_register.html",
            {
                "request": request, 
                "entries": entries,
                "today": date.today(),
                "is_admin": token_data.get("is_admin", False)
            }
        )
    except Exception as e:
        logger.error(f"Cash register error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.post("/entries")
async def create_cash_entry(request: Request, entry: CashEntry):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")

        entry_dict = entry.dict()
        entry_dict["created_by"] = token_data["username"]
        result = await db.cash_register.insert_one(entry_dict)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Create entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Update API routes to use token auth
@api_router.get("/entries", response_model=List[CashRegister])
async def get_cash_entries(
    request: Request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Rest of the function remains the same
        query = {}
        if start_date and end_date:
            query["date"] = {
                "$gte": datetime.combine(start_date, datetime.min.time()),
                "$lte": datetime.combine(end_date, datetime.max.time())
            }
        entries = await db.cash_register.find(query).sort("date", -1).to_list(1000)
        return entries
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/entries/{entry_id}", response_model=CashRegister)
async def update_cash_entry(
    request: Request,
    entry_id: str,
    entry_update: CashRegister
):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data or not token_data.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized")

        update_result = await db.cash_register.update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": entry_update.dict(exclude_unset=True)}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return await db.cash_register.find_one({"_id": ObjectId(entry_id)})
    except Exception as e:
        logger.error(f"Update entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/entries/{entry_id}")
async def delete_cash_entry(request: Request, entry_id: str):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data or not token_data.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized")

        result = await db.cash_register.delete_one({"_id": ObjectId(entry_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return {"message": "Entry deleted successfully"}
    except Exception as e:
        logger.error(f"Delete entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Export the combined router
web_router.include_router(api_router)
router = web_router