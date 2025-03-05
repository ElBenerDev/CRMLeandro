from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
from ..database import get_db
import logging
import csv
from io import StringIO
from bson import ObjectId
from pymongo import UpdateOne

logger = logging.getLogger(__name__)

web_router = APIRouter()
api_router = APIRouter(prefix="/api/inventory", tags=["inventory"])
templates = Jinja2Templates(directory="app/templates")

class InventoryItem(BaseModel):
    name: str
    current_stock: float
    unit: str
    to_order: float = 0
    supplier: str
    category: str
    min_stock: float = 0
    max_stock: float = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    location: str = ""
    notes: str = ""

    class Config:
        from_attributes = True

async def get_user_from_token(request: Request, db):
    token = request.cookies.get("access_token")
    if not token:
        return None
    return await db.active_tokens.find_one({"token": token})

@web_router.get("/inventory", name="inventory.index")
async def inventory_page(request: Request):
    """Display inventory page"""
    try:
        db = await get_db()
        inventory = await db.inventory.find().to_list(None)
        return templates.TemplateResponse(
            "inventory.html",
            {"request": request, "inventory": inventory}
        )
    except Exception as e:
        logger.error(f"Inventory error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.get("/inventory/alerts")
async def inventory_alerts(request: Request):
    """Show items that need reordering"""
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        if not token_data:
            return RedirectResponse(url="/login")

        low_stock_items = await db.inventory.find({
            "$expr": {
                "$lte": ["$current_stock", "$min_stock"]
            }
        }).to_list(None)
        
        return templates.TemplateResponse(
            "inventory_alerts.html",
            {
                "request": request,
                "alerts": low_stock_items,
                "is_admin": token_data.get("is_admin", False)
            }
        )
    except Exception as e:
        logger.error(f"Error in alerts view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.post("/inventory/add")
async def add_item(
    request: Request,
    name: str = Form(...),
    current_stock: float = Form(...),
    unit: str = Form(...),
    supplier: str = Form(...)
):
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        if not token_data:
            raise HTTPException(status_code=403)
            
        item = InventoryItem(
            name=name,
            current_stock=current_stock,
            unit=unit,
            to_order=0,
            supplier=supplier
        )
        
        await db.inventory.insert_one(item.model_dump())
        return RedirectResponse(url="/inventory", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "inventory.html",
            {
                "request": request,
                "error": str(e),
                "inventory": await db.inventory.find().to_list(None)
            },
            status_code=400
        )

@web_router.get("/inventory/export")
async def export_inventory(
    request: Request,
    format: str = Query("csv", enum=["csv", "excel", "pdf"])
):
    """Export inventory in different formats"""
    db = await get_db()
    items = await db.inventory.find().to_list(None)
    
    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "current_stock", "unit", "supplier"])
        writer.writeheader()
        writer.writerows(items)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory.csv"}
        )

@web_router.get("/inventory/search")
async def search_inventory(
    request: Request,
    q: str = None,
    supplier: str = None,
    category: str = None,
    low_stock: bool = False
):
    """Search and filter inventory items"""
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"supplier": {"$regex": q, "$options": "i"}}
        ]
    if supplier:
        query["supplier"] = supplier
    if category:
        query["category"] = category
    if low_stock:
        query["$expr"] = {"$lte": ["$current_stock", "$min_stock"]}
        
    db = await get_db()
    items = await db.inventory.find(query).to_list(None)
    return templates.TemplateResponse(
        "inventory.html",
        {
            "request": request,
            "inventory": items,
            "search": q,
            "filters": {"supplier": supplier, "category": category, "low_stock": low_stock}
        }
    )

@web_router.get("/inventory/dashboard")
async def inventory_dashboard(request: Request):
    """Show inventory statistics and charts"""
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        
        total_items = await db.inventory.count_documents({})
        
        supplier_stats = await db.inventory.aggregate([
            {"$group": {
                "_id": "$supplier",
                "count": {"$sum": 1},
                "total_stock": {"$sum": "$current_stock"}
            }},
            {"$sort": {"count": -1}}
        ]).to_list(None)

        low_stock_items = await db.inventory.find({
            "current_stock": {"$lt": 10}
        }).to_list(None)

        stats = {
            "total_items": total_items,
            "low_stock_count": len(low_stock_items),
            "supplier_count": len(supplier_stats),
            "suppliers": {stat["_id"]: stat["count"] for stat in supplier_stats}
        }

        suppliers = [stat["_id"] for stat in supplier_stats]
        supplier_counts = [stat["count"] for stat in supplier_stats]
        supplier_stocks = [stat["total_stock"] for stat in supplier_stats]

        return templates.TemplateResponse(
            "inventory_dashboard.html",
            {
                "request": request,
                "stats": stats,
                "suppliers": suppliers,
                "supplier_counts": supplier_counts,
                "supplier_stocks": supplier_stocks,
                "low_stock_items": low_stock_items,
                "is_admin": token_data.get("is_admin", False) if token_data else False
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard view: {e}")
        return templates.TemplateResponse(
            "inventory_dashboard.html",
            {
                "request": request,
                "error": str(e),
                "stats": {},
                "is_admin": False
            }
        )

@web_router.get("/inventory/movements")
async def stock_movements(request: Request):
    """View stock movement history"""
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        if not token_data:
            return RedirectResponse(url="/login")
            
        movements = await db.stock_movements.aggregate([
            {
                "$lookup": {
                    "from": "inventory",
                    "localField": "item_id",
                    "foreignField": "_id",
                    "as": "item"
                }
            },
            {"$unwind": "$item"},
            {"$sort": {"timestamp": -1}},
            {"$limit": 100}
        ]).to_list(None)
        
        return templates.TemplateResponse(
            "stock_movements.html",
            {
                "request": request,
                "movements": movements,
                "is_admin": token_data.get("is_admin", False)
            }
        )
    except Exception as e:
        logger.error(f"Error in movements view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/", response_model=List[InventoryItem])
async def get_inventory():
    db = await get_db()
    items = await db.inventory.find().to_list(None)
    return items

@api_router.post("/", response_model=InventoryItem)
async def create_inventory_item(request: Request, item: InventoryItem):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data:
        raise HTTPException(status_code=403, detail="Not authenticated")
        
    item_dict = item.model_dump()
    result = await db.inventory.insert_one(item_dict)
    created_item = await db.inventory.find_one({"_id": result.inserted_id})
    return created_item

@api_router.put("/{item_id}", response_model=InventoryItem)
async def update_inventory_item(item_id: str, item: InventoryItem, request: Request):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data:
        raise HTTPException(status_code=403, detail="Not authenticated")
        
    result = await db.inventory.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": item.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated_item = await db.inventory.find_one({"_id": ObjectId(item_id)})
    return updated_item

@api_router.delete("/{item_id}")
async def delete_inventory_item(item_id: str, request: Request):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data or not token_data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
        
    result = await db.inventory.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@api_router.post("/reset", response_model=dict)
async def reset_inventory_endpoint(request: Request):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data or not token_data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    try:
        await db.inventory.drop()
        await db.inventory.create_index("name", unique=True)
        return {"message": "Inventory reset successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.patch("/{item_id}")
async def update_stock(item_id: str, request: Request):
    """Update inventory item stock"""
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        if not token_data:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        data = await request.json()
        new_stock = float(data.get('current_stock', 0))
        
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        movement = {
            "item_id": ObjectId(item_id),
            "item_name": item["name"],
            "previous_stock": item["current_stock"],
            "new_stock": new_stock,
            "change": new_stock - item["current_stock"],
            "user": token_data["username"],
            "timestamp": datetime.utcnow()
        }

        await db.stock_movements.insert_one(movement)

        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {
                "$set": {
                    "current_stock": new_stock,
                    "last_updated": datetime.utcnow(),
                    "last_updated_by": token_data["username"]
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No update performed")

        return {
            "success": True,
            "new_stock": new_stock,
            "message": "Stock updated successfully"
        }

    except Exception as e:
        logger.error(f"Error updating stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/movements/{item_id}")
async def get_stock_movements(item_id: str, request: Request):
    """Get stock movement history for an item"""
    try:
        db = await get_db()
        token_data = await get_user_from_token(request, db)
        if not token_data:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        movements = await db.stock_movements.find(
            {"item_id": ObjectId(item_id)}
        ).sort("timestamp", -1).to_list(length=50)
        
        for movement in movements:
            movement["_id"] = str(movement["_id"])
            movement["item_id"] = str(movement["item_id"])
            movement["timestamp"] = movement["timestamp"].isoformat()
            
        return movements
    except Exception as e:
        logger.error(f"Error getting stock movements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

web_router.include_router(api_router)
router = web_router