from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
from ..database import db
import logging
import csv
from io import StringIO
from bson import ObjectId

logger = logging.getLogger(__name__)

# Create two separate routers
web_router = APIRouter()
api_router = APIRouter(prefix="/api/inventory", tags=["inventory"])

templates = Jinja2Templates(directory="app/templates")

# Convert to Pydantic model
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

# Web routes
@web_router.get("/inventory")
async def inventory_page(request: Request):
    """Display inventory page"""
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
        
    try:
        # Get all inventory items from MongoDB
        inventory_items = await db.inventory.find().to_list(None)
        
        # Convert ObjectId to string for JSON serialization
        for item in inventory_items:
            item["_id"] = str(item["_id"])
        
        return templates.TemplateResponse(
            "inventory.html",
            {
                "request": request,
                "inventory": inventory_items,
                "is_admin": request.session.get("is_admin", False)
            }
        )
    except Exception as e:
        logger.error(f"Error in inventory view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.get("/inventory/alerts")
async def inventory_alerts(request: Request):
    """Show items that need reordering"""
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    
    try:
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
                "is_admin": request.session.get("is_admin", False)
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
    if not request.session.get("user"):
        raise HTTPException(status_code=403)
        
    item = InventoryItem(
        name=name,
        current_stock=current_stock,
        unit=unit,
        to_order=0,
        supplier=supplier
    )
    
    try:
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
    if not request.session.get("user"):
        return RedirectResponse(url="/login")

    try:
        # Basic stats
        total_items = await db.inventory.count_documents({})
        
        # Get supplier stats
        supplier_stats = await db.inventory.aggregate([
            {"$group": {
                "_id": "$supplier",
                "count": {"$sum": 1},
                "total_stock": {"$sum": "$current_stock"}
            }},
            {"$sort": {"count": -1}}
        ]).to_list(None)

        # Get low stock items
        low_stock_items = await db.inventory.find({
            "current_stock": {"$lt": 10}  # Adjust threshold as needed
        }).to_list(None)

        stats = {
            "total_items": total_items,
            "low_stock_count": len(low_stock_items),
            "supplier_count": len(supplier_stats),
            "suppliers": {stat["_id"]: stat["count"] for stat in supplier_stats}
        }

        # Prepare chart data
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
                "is_admin": request.session.get("is_admin", False)
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
                "is_admin": request.session.get("is_admin", False)
            }
        )

@web_router.get("/inventory/movements")
async def stock_movements(request: Request):
    """View stock movement history"""
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
        
    try:
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
                "is_admin": request.session.get("is_admin", False)
            }
        )
    except Exception as e:
        logger.error(f"Error in movements view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API routes
@api_router.get("/", response_model=List[InventoryItem])
async def get_inventory():
    items = await db.inventory.find().to_list(None)
    return items

@api_router.post("/", response_model=InventoryItem)
async def create_inventory_item(item: InventoryItem):
    item_dict = item.model_dump()
    result = await db.inventory.insert_one(item_dict)
    created_item = await db.inventory.find_one({"_id": result.inserted_id})
    return created_item

@api_router.put("/{item_id}", response_model=InventoryItem)
async def update_inventory_item(item_id: str, item: InventoryItem):
    result = await db.inventory.update_one(
        {"_id": item_id},
        {"$set": item.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated_item = await db.inventory.find_one({"_id": item_id})
    return updated_item

@api_router.delete("/{item_id}")
async def delete_inventory_item(item_id: str):
    result = await db.inventory.delete_one({"_id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@api_router.post("/reset", response_model=dict)
async def reset_inventory_endpoint(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    try:
        await db.inventory.drop()
        await db.inventory.create_index("name", unique=True)
        await db.inventory.insert_many(DEFAULT_INVENTORY)
        return {"message": f"Reset {len(DEFAULT_INVENTORY)} inventory items"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/{item_id}/movement")
async def record_stock_movement(
    item_id: str,
    quantity: float,
    movement_type: str,  # "in" or "out"
    notes: str = None
):
    """Record stock movements with audit trail"""
    movement = {
        "item_id": item_id,
        "quantity": quantity,
        "type": movement_type,
        "timestamp": datetime.utcnow(),
        "user": request.session.get("user"),
        "notes": notes
    }
    
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            # Update current stock
            multiplier = 1 if movement_type == "in" else -1
            result = await db.inventory.update_one(
                {"_id": item_id},
                {"$inc": {"current_stock": quantity * multiplier}}
            )
            
            # Record movement
            await db.stock_movements.insert_one(movement)
            
            return {"message": "Stock movement recorded"}

@api_router.post("/bulk-update")
async def bulk_update_inventory(items: List[InventoryItem]):
    """Update multiple items at once"""
    operations = []
    for item in items:
        operations.append(
            UpdateOne(
                {"name": item.name},
                {"$set": item.model_dump(exclude={"name"})},
                upsert=True
            )
        )
    
    result = await db.inventory.bulk_write(operations)
    return {
        "modified": result.modified_count,
        "upserted": result.upserted_count
    }

@api_router.patch("/{item_id}")
async def update_stock(item_id: str, request: Request):
    """Update inventory item stock"""
    try:
        data = await request.json()
        new_stock = float(data.get('current_stock', 0))
        
        # Get current item
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Create movement record
        movement = {
            "item_id": ObjectId(item_id),
            "item_name": item["name"],
            "previous_stock": item["current_stock"],
            "new_stock": new_stock,
            "change": new_stock - item["current_stock"],
            "user": request.session.get("user", "unknown"),
            "timestamp": datetime.utcnow()
        }

        # Insert movement first
        await db.stock_movements.insert_one(movement)

        # Update inventory
        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {
                "$set": {
                    "current_stock": new_stock,
                    "last_updated": datetime.utcnow(),
                    "last_updated_by": request.session.get("user", "unknown")
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

# Add this route to see stock movements
@api_router.get("/movements/{item_id}")
async def get_stock_movements(item_id: str, request: Request):
    """Get stock movement history for an item"""
    try:
        movements = await db.stock_movements.find(
            {"item_id": ObjectId(item_id)}
        ).sort("timestamp", -1).to_list(length=50)
        
        # Convert ObjectId to string for JSON
        for movement in movements:
            movement["_id"] = str(movement["_id"])
            movement["item_id"] = str(movement["item_id"])
            movement["timestamp"] = movement["timestamp"].isoformat()
            
        return movements
    except Exception as e:
        logger.error(f"Error getting stock movements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export the web router as the main router
router = web_router