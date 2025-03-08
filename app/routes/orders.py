from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from typing import List
from ..models.order import Order, OrderItem
from ..dependencies import get_current_user
from ..database import db, get_db
from bson import ObjectId
import logging
from datetime import datetime
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

async def get_low_stock_items(db):
    """Get items that are below minimum stock levels"""
    try:
        pipeline = [
            {
                "$match": {
                    "current_stock": {"$exists": True},  # Ensure current_stock exists
                    "$expr": {
                        "$or": [
                            {"$lte": ["$current_stock", "$min_stock"]},  # At or below minimum
                            {"$eq": ["$current_stock", 0]}  # Out of stock
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "suggested_order": {
                        "$subtract": [
                            {"$ifNull": ["$max_stock", 30]},  # Default max_stock to 30
                            "$current_stock"
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "priority": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": ["$current_stock", 0]}, "then": 1},  # Out of stock
                                {
                                    "case": {
                                        "$lt": ["$current_stock", {"$ifNull": ["$min_stock", 5]}]
                                    }, 
                                    "then": 2
                                }  # Below min
                            ],
                            "default": 3
                        }
                    }
                }
            },
            {
                "$sort": {
                    "priority": 1,
                    "supplier": 1,
                    "name": 1
                }
            }
        ]

        items = await db.inventory.aggregate(pipeline).to_list(None)
        
        # Add debug logging
        logger.debug(f"Found {len(items)} items below minimum stock")
        for item in items:
            logger.debug(
                f"Low stock item: {item['name']} - "
                f"Current: {item['current_stock']} - "
                f"Min: {item.get('min_stock', 5)} - "
                f"Max: {item.get('max_stock', 30)} - "
                f"Suggested: {item['suggested_order']}"
            )
        
        return items
        
    except Exception as e:
        logger.error(f"Error in get_low_stock_items: {str(e)}", exc_info=True)
        return []

@router.get("/orders", name="orders.index")
async def get_orders(request: Request):
    try:
        logger.debug("Getting orders page")
        db = await get_db()
        
        orders = await db.orders.find().sort("created_at", -1).to_list(None)
        logger.debug(f"Found {len(orders)} orders")
        
        suggested_items = await get_low_stock_items(db)
        logger.debug(f"Found {len(suggested_items)} suggested items")
        
        # Safer debug logging
        for item in suggested_items:
            logger.debug(
                f"Suggestion: {item.get('name', 'N/A')} - "
                f"Current: {item.get('current_stock', 0)} - "
                f"Min: {item.get('min_stock', 5)}"
            )
        
        return templates.TemplateResponse(
            "orders.html",
            {
                "request": request,
                "user": request.state.user,
                "is_admin": getattr(request.state.user, "is_admin", False),
                "orders": orders,
                "suggested_items": suggested_items,
                "active_page": "orders"
            }
        )
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders")
async def create_order(order: Order):
    order_dict = order.dict()
    result = await db.orders.insert_one(order_dict)
    return {"id": str(result.inserted_id)}

@router.post("/api/orders/create-from-suggestion")
async def create_order_from_suggestion(request: Request):
    """Create an order from a suggested item"""
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        data = await request.json()
        item_id = data.get("item_id")
        
        if not item_id:
            raise HTTPException(status_code=400, detail="Item ID is required")
            
        db = await get_db()
        
        # Find the suggestion containing this item
        suggestion = await db.order_suggestions.find_one({
            "items.item_id": item_id,
            "status": "pending"
        })
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
            
        # Find the specific item in the suggestion
        suggested_item = next(
            (item for item in suggestion["items"] if item["item_id"] == item_id),
            None
        )
        
        if not suggested_item:
            raise HTTPException(status_code=404, detail="Item not found in suggestion")
        
        # Create order
        order = {
            "client": "INTERNAL",
            "created_by": user["username"],
            "created_at": datetime.utcnow(),
            "status": "PENDING",
            "type": "restock",
            "description": f"Restock order for {suggested_item['name']}",
            "items": [suggested_item],
            "amount": 0,  # You might want to calculate this based on item cost
            "source_suggestion": str(suggestion["_id"])
        }
        
        # Insert order and update suggestion
        result = await db.orders.insert_one(order)
        
        # Update suggestion to mark this item as processed
        await db.order_suggestions.update_one(
            {"_id": suggestion["_id"], "items.item_id": item_id},
            {"$set": {
                "items.$.status": "processed",
                "updated_at": datetime.utcnow()
            }}
        )
        
        logger.info(f"Created order {result.inserted_id} from suggestion for item {item_id}")
        
        return JSONResponse({
            "success": True,
            "order_id": str(result.inserted_id)
        })
        
    except Exception as e:
        logger.error(f"Error creating order from suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily-cash")
async def get_daily_cash(current_user = Depends(get_current_user)):
    cash_entries = await db.daily_cash.find().to_list(1000)
    return cash_entries

@router.get("/api/orders/suggestions/count")
async def get_suggestions_count():
    """Get count of pending order suggestions"""
    try:
        db = await get_db()
        count = await db.order_suggestions.count_documents({"status": "pending"})
        return {"count": count}
    except Exception as e:
        logger.error(f"Error getting suggestions count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))