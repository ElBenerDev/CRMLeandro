from fastapi import APIRouter, Depends
from typing import List
from ..models.order import Order
from ..dependencies import get_current_user
from ..database import db
from bson import ObjectId

router = APIRouter()

@router.get("/orders", response_model=List[Order])
async def get_orders():
    orders = await db.orders.find().to_list(1000)
    return [Order(**order) for order in orders]

@router.post("/orders")
async def create_order(order: Order):
    order_dict = order.dict()
    result = await db.orders.insert_one(order_dict)
    return {"id": str(result.inserted_id)}

@router.get("/daily-cash")
async def get_daily_cash(current_user = Depends(get_current_user)):
    cash_entries = await db.daily_cash.find().to_list(1000)
    return cash_entries