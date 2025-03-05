from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from typing import List
from ..models.order import Order
from ..dependencies import get_current_user
from ..database import db, get_db
from bson import ObjectId
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

@router.get("/orders", name="orders.index")
async def get_orders(request: Request):
    """Get all orders"""
    try:
        db = await get_db()
        orders = await db.orders.find().to_list(None)
        return templates.TemplateResponse(
            "orders.html",
            {"request": request, "orders": orders}
        )
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders")
async def create_order(order: Order):
    order_dict = order.dict()
    result = await db.orders.insert_one(order_dict)
    return {"id": str(result.inserted_id)}

@router.get("/daily-cash")
async def get_daily_cash(current_user = Depends(get_current_user)):
    cash_entries = await db.daily_cash.find().to_list(1000)
    return cash_entries