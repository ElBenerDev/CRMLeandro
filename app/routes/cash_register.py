from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime, date
from bson import ObjectId
from fastapi.templating import Jinja2Templates
from ..models.cash_register import CashRegister, CashEntry
from ..dependencies import get_current_user
from ..database import db

router = APIRouter(prefix="/api/cash-register", tags=["cash_register"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=List[CashRegister])
async def get_cash_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user = Depends(get_current_user)
):
    query = {}
    if start_date and end_date:
        query["date"] = {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date, datetime.max.time())
        }
    
    entries = await db.cash_register.find(query).sort("date", -1).to_list(1000)
    return entries

@router.get("/cash-register")
async def get_cash_register(request: Request):
    entries = await db.cash_register.find().sort("date", -1).to_list(100)
    return templates.TemplateResponse(
        "cash_register.html",
        {
            "request": request, 
            "entries": entries,
            "today": date.today()
        }
    )

@router.post("/", response_model=CashRegister)
async def create_cash_entry(
    entry: CashRegister,
    current_user = Depends(get_current_user)
):
    entry_dict = entry.dict()
    entry_dict["created_by"] = current_user.username
    result = await db.cash_register.insert_one(entry_dict)
    created_entry = await db.cash_register.find_one({"_id": result.inserted_id})
    return created_entry

@router.post("/cash-register")
async def create_cash_entry(entry: CashEntry):
    entry_dict = entry.dict()
    result = await db.cash_register.insert_one(entry_dict)
    return {"id": str(result.inserted_id)}

@router.put("/{entry_id}", response_model=CashRegister)
async def update_cash_entry(
    entry_id: str,
    entry_update: CashRegister,
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update entries")
    
    update_result = await db.cash_register.update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": entry_update.dict(exclude_unset=True)}
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return await db.cash_register.find_one({"_id": ObjectId(entry_id)})

@router.delete("/{entry_id}")
async def delete_cash_entry(
    entry_id: str,
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete entries")
    
    result = await db.cash_register.delete_one({"_id": ObjectId(entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"message": "Entry deleted successfully"}