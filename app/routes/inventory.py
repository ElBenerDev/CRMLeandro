from fastapi import APIRouter, Request, Form, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse  # Add JSONResponse here
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId
from ..database import get_db
from ..services.inventory import get_inventory_state
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Setup templates
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

class WeeklyCount(BaseModel):
    count_date: datetime
    counted_by: str
    items: List[dict]
    status: str = "pending"
    notes: Optional[str] = None

async def get_user_from_token(request: Request, db):
    token = request.cookies.get("access_token")
    if not token:
        return None
    return await db.active_tokens.find_one({"token": token})

async def check_inventory_access(request: Request):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return user

@router.get("/inventory", name="inventory.index")
async def inventory_page(request: Request):
    try:
        user = request.state.user
        if not user:
            logger.warning("No user found in request state")
            return RedirectResponse(url="/login")

        db = await get_db()
        
        # Get inventory state with debug logging
        state = await get_inventory_state(user)
        logger.debug(f"Got inventory state: {state}")

        # Get inventory items
        inventory_items = await db.inventory.find().sort("name", 1).to_list(None)

        template_data = {
            "request": request,
            "user": user,
            "inventory": inventory_items,
            "is_admin": state["is_admin"],
            "is_count_day": state["is_count_day"],
            "is_counting": state["is_counting"]
        }

        return templates.TemplateResponse("inventory.html", template_data)
        
    except Exception as e:
        logger.error(f"Inventory error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory/alerts")
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

@router.post("/inventory/add")
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

@router.get("/inventory/export")
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

@router.get("/inventory/search")
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

@router.get("/inventory/dashboard")
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

@router.get("/inventory/movements")
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

@router.get("/api/inventory", response_model=List[InventoryItem])
async def get_inventory():
    db = await get_db()
    items = await db.inventory.find().to_list(None)
    return items

@router.post("/api/inventory", response_model=InventoryItem)
async def create_inventory_item(request: Request, item: InventoryItem):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data:
        raise HTTPException(status_code=403, detail="Not authenticated")
        
    item_dict = item.model_dump()
    result = await db.inventory.insert_one(item_dict)
    created_item = await db.inventory.find_one({"_id": result.inserted_id})
    return created_item

@router.put("/api/inventory/{item_id}", response_model=InventoryItem)
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

@router.delete("/api/inventory/{item_id}")
async def delete_inventory_item(item_id: str, request: Request):
    db = await get_db()
    token_data = await get_user_from_token(request, db)
    if not token_data or not token_data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
        
    result = await db.inventory.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@router.post("/api/inventory/reset", response_model=dict)
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

@router.patch("/api/inventory/{item_id}")
async def update_stock(item_id: str, request: Request):
    """Allow both admin and regular users to update stock counts"""
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")

        body = await request.json()
        new_stock = float(body.get("current_stock", 0))
        
        db = await get_db()
        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"current_stock": new_stock}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
            
        return {"success": True, "new_stock": new_stock}
    except Exception as e:
        logger.error(f"Error updating stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/inventory/movements/{item_id}")
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

@router.post("/api/inventory/movement")
async def register_movement(
    request: Request,
    item_id: str = Form(...),
    quantity: float = Form(...),
    movement_type: str = Form(...),  # "add" or "subtract"
    notes: str = Form(None)
):
    try:
        user = request.state.user
        db = await get_db()
        
        # Validate item exists
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Calculate new stock
        current_stock = item["current_stock"]
        quantity = abs(float(quantity))  # Ensure positive number
        
        if movement_type == "subtract":
            quantity = -quantity
            
        new_stock = current_stock + quantity

        # Create movement record
        movement = {
            "item_id": ObjectId(item_id),
            "user_id": ObjectId(user["_id"]),
            "quantity": quantity,
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "timestamp": datetime.utcnow(),
            "notes": notes,
            "username": user["username"]
        }

        # Update stock and save movement
        await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"current_stock": new_stock}}
        )
        await db.stock_movements.insert_one(movement)

        return {"success": True, "new_stock": new_stock}

    except Exception as e:
        logger.error(f"Error registering movement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inventory/items")
async def add_item(request: Request):
    try:
        user = request.state.user
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
            
        # Get request body
        data = await request.json()
        
        # Validate required fields
        required_fields = ["name", "current_stock", "unit", "supplier", "category"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        db = await get_db()
        
        # Check if item with same name exists
        existing_item = await db.inventory.find_one({"name": data["name"]})
        if existing_item:
            raise HTTPException(status_code=400, detail="Item with this name already exists")
        
        # Create new item document
        new_item = {
            "name": data["name"],
            "current_stock": float(data["current_stock"]),
            "unit": data["unit"],
            "supplier": data["supplier"],
            "category": data["category"],
            "min_stock": float(data.get("min_stock", 0)),
            "max_stock": float(data.get("max_stock", 0)),
            "location": data.get("location", ""),
            "notes": data.get("notes", ""),
            "last_count": None,
            "created_at": datetime.utcnow(),
            "created_by": user["username"]
        }
        
        # Insert the new item
        result = await db.inventory.insert_one(new_item)
        
        # Log the action
        logger.info(f"New item added: {new_item['name']} by {user['username']}")
        
        # Create initial stock movement record
        if float(new_item["current_stock"]) > 0:
            movement = {
                "item_id": result.inserted_id,
                "user_id": ObjectId(user["_id"]),
                "quantity": float(new_item["current_stock"]),
                "previous_stock": 0,
                "new_stock": float(new_item["current_stock"]),
                "timestamp": datetime.utcnow(),
                "notes": "Initial stock",
                "username": user["username"]
            }
            await db.stock_movements.insert_one(movement)
        
        # Return the created item
        return {
            "message": "Item added successfully",
            "item_id": str(result.inserted_id),
            "name": new_item["name"]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inventory/start-count")
async def start_count(request: Request):
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        db = await get_db()
        
        # Check for existing active count
        existing_count = await db.count_sessions.find_one({
            "user_id": ObjectId(user["_id"]),
            "status": "in_progress"
        })
        
        if existing_count:
            raise HTTPException(status_code=400, detail="Active count already exists")
        
        # Create new count session
        count_session = {
            "user_id": ObjectId(user["_id"]),
            "started_at": datetime.utcnow(),
            "status": "in_progress"
        }
        
        await db.count_sessions.insert_one(count_session)
        return {"success": True, "message": "Count session started"}
        
    except Exception as e:
        logger.error(f"Error starting count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/api/inventory/{item_id}/update-stock")
async def update_stock(item_id: str, request: Request):
    """Update stock level for an item"""
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        # Get the new stock value from request body
        body = await request.json()
        new_stock = float(body.get("current_stock", 0))
        
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stock cannot be negative")
            
        db = await get_db()
        
        # Get current item to record movement
        current_item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not current_item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        # Calculate movement quantity
        movement_quantity = new_stock - current_item["current_stock"]
        
        # Update stock
        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "current_stock": new_stock,
                "last_updated": datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
            
        # Record movement
        movement = {
            "item_id": ObjectId(item_id),
            "user_id": ObjectId(user["_id"]),
            "quantity": movement_quantity,
            "previous_stock": current_item["current_stock"],
            "new_stock": new_stock,
            "timestamp": datetime.utcnow(),
            "notes": "Manual stock update",
            "username": user["username"]
        }
        
        await db.stock_movements.insert_one(movement)
            
        return {
            "success": True,
            "new_stock": new_stock,
            "unit": current_item["unit"]
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inventory/weekly-count")
async def submit_weekly_count(request: Request):
    """Handle weekly inventory count submission"""
    try:
        user = request.state.user
        if not user or 'perform_count' not in user.get('permissions', []):
            raise HTTPException(status_code=403, detail="Not authorized to perform count")
            
        data = await request.json()
        logger.debug(f"Received weekly count data: {data}")

        items = data.get("items", [])
        notes = data.get("notes", "")
        
        if not items:
            raise HTTPException(status_code=400, detail="No items provided")

        db = await get_db()
        
        # Create weekly count record
        count_session = {
            "user_id": ObjectId(user["_id"]),
            "count_date": datetime.utcnow(),
            "items": items,
            "notes": notes,
            "status": "completed"
        }
        
        result = await db.weekly_counts.insert_one(count_session)
        logger.info(f"Created weekly count session: {result.inserted_id}")

        # Update inventory and record movements
        for item in items:
            item_id = ObjectId(item["item_id"])
            current_stock = float(item["current_stock"])
            counted_stock = float(item["counted_stock"])
            difference = counted_stock - current_stock
            
            # Update stock
            await db.inventory.update_one(
                {"_id": item_id},
                {"$set": {
                    "current_stock": counted_stock,
                    "last_count": datetime.utcnow()
                }}
            )
            
            # Record movement
            await db.stock_movements.insert_one({
                "item_id": item_id,
                "user_id": ObjectId(user["_id"]),
                "quantity": difference,
                "previous_stock": current_stock,
                "new_stock": counted_stock,
                "timestamp": datetime.utcnow(),
                "notes": f"Ajuste por conteo semanal: {notes}",
                "username": user["username"],
                "type": "weekly_count"
            })
            
            logger.info(f"Updated item {item_id}: {current_stock} -> {counted_stock} (diff: {difference})")
        
        return JSONResponse({"success": True, "message": "Weekly count recorded successfully"})
        
    except Exception as e:
        logger.error(f"Error in weekly count: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))