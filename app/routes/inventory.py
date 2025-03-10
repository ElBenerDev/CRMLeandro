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

# Add these constants at the top of the file
DEFAULT_CATEGORIES = [
    "BEBIDAS",
    "CONDIMENTOS",
    "DESECHABLES",
    "EQUIPO",
    "HELADOS",
    "INSUMOS BÁSICOS",
    "LIMPIEZA",
    "MANTENIMIENTO",
    "PACKAGING",
    "PERECEDEROS"
]

# Add this constant with your other constants
SUPPLIER_CATEGORY_MAP = {
    'ACACIAS': 'PERECEDEROS',
    'AMAZON': 'INSUMOS BÁSICOS',
    'CARLOS ROLLOS PACK': 'PACKAGING',
    'COSTCO': 'INSUMOS BÁSICOS',
    'DEPOT': 'EQUIPO',
    'INSTACAR': 'INSUMOS BÁSICOS',
    'LIZ': 'LIMPIEZA',
    'MARIANO': 'PERECEDEROS',
    'ROMANO': 'BEBIDAS',
    'SANBER': 'BEBIDAS',
    'SYSCO': 'INSUMOS BÁSICOS',
    'TQMUCH': 'CONDIMENTOS',
    'WALLMART': 'INSUMOS BÁSICOS',
    'WEBRESTAURANT': 'EQUIPO'
}

class InventoryItem(BaseModel):
    name: str
    current_stock: float
    unit: str = ""
    to_order: float = 0
    supplier: str = ""
    category: str = "Sin Categoría"
    min_stock: float = Field(default=0, description="Minimum stock level")
    max_stock: float = Field(default=0, description="Maximum stock level")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    location: str = ""
    notes: str = ""

    class Config:
        from_attributes = True
        json_encoders = {
            ObjectId: str
        }

class WeeklyCount(BaseModel):
    count_date: datetime
    counted_by: str
    items: List[dict]
    status: str = "pending"
    notes: Optional[str] = None

# Add this new model class
class StockMovement(BaseModel):
    quantity: float
    notes: str
    movement_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            ObjectId: str
        }

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
            return RedirectResponse(url="/login")

        db = await get_db()
        
        # Find all inventory items with fresh data
        cursor = db.inventory.find().sort("name", 1)
        inventory_items = []
        
        async for doc in cursor:
            # Process each document
            item = {
                "_id": str(doc["_id"]),
                "name": doc["name"],
                "current_stock": float(doc.get("current_stock", 0)),
                "unit": doc.get("unit", ""),
                "supplier": doc.get("supplier", ""),
                "category": doc.get("category", "Sin Categoría"),
                "min_stock": float(doc.get("min_stock", 5.0)),
                "max_stock": float(doc.get("max_stock", 30.0)),
                "last_count": doc.get("last_count"),
                "last_updated": doc.get("last_updated"),
                "last_updated_by": doc.get("last_updated_by")
            }
            inventory_items.append(item)

        return templates.TemplateResponse("inventory.html", {
            "request": request,
            "user": user,
            "inventory": inventory_items,
            "is_admin": user.get("is_admin", False),
            "is_count_day": True,
            "is_counting": False,
            "DEFAULT_CATEGORIES": DEFAULT_CATEGORIES,
            "SUPPLIER_CATEGORY_MAP": SUPPLIER_CATEGORY_MAP
        })
        
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

@router.patch("/api/inventory/{item_id}/update-stock")
async def update_stock(item_id: str, request: Request):
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        # Check if user has permission to add stock
        if "add_stock" not in user["permissions"] and not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized to modify stock")

        body = await request.json()
        movement_type = body.get("movement_type", "add")
        
        # Regular users can only add stock
        if not user.get("is_admin") and movement_type != "add":
            raise HTTPException(status_code=403, detail="Regular users can only add stock")

        new_stock = float(body.get("current_stock", 0))
        notes = body.get("notes", "")
        
        db = await get_db()
        
        # Get current item
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        current_stock = item.get("current_stock", 0)
        
        # Calculate stock change
        quantity = abs(new_stock - current_stock)
        if movement_type == "subtract":
            quantity = -quantity

        new_stock = current_stock + quantity

        # Record movement
        movement = {
            "item_id": ObjectId(item_id),
            "item_name": item["name"],
            "user_id": ObjectId(user["_id"]),
            "username": user["username"],
            "quantity": quantity,
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "timestamp": datetime.utcnow(),
            "notes": notes,
            "movement_type": movement_type
        }

        await db.stock_movements.insert_one(movement)
            
        # Update stock
        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "current_stock": new_stock,
                "last_updated": datetime.utcnow(),
                "last_updated_by": user["username"]
            }}
        )

        return JSONResponse({
            "success": True,
            "new_stock": new_stock,
            "movement": {
                "quantity": quantity,
                "timestamp": movement["timestamp"].isoformat(),
                "username": user["username"],
                "notes": notes
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating stock: {str(e)}", exc_info=True)
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

@router.post("/api/inventory/weekly-count")
async def submit_weekly_count(request: Request):
    """Handle weekly inventory count submission"""
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")

        data = await request.json()
        logger.debug(f"Received weekly count data: {data}")

        items = data.get("items", [])
        notes = data.get("notes", "")
        
        if not items:
            raise HTTPException(status_code=400, detail="No items provided")

        db = await get_db()
        items_below_min = []
        
        # Create weekly count record
        count_session = {
            "user_id": ObjectId(user["_id"]),
            "username": user["username"],
            "count_date": datetime.utcnow(),
            "items": items,
            "notes": notes,
            "status": "completed"
        }
        
        result = await db.weekly_counts.insert_one(count_session)
        logger.info(f"Created weekly count session: {result.inserted_id}")

        # Update inventory and record movements
        for item in items:
            item_id = item["item_id"]
            current_stock = item["current_stock"]
            counted_stock = item["counted_stock"]
            
            # Record movement
            movement = {
                "item_id": ObjectId(item_id),
                "user_id": ObjectId(user["_id"]),
                "username": user["username"],
                "quantity": counted_stock - current_stock,
                "previous_stock": current_stock,
                "new_stock": counted_stock,
                "timestamp": datetime.utcnow(),
                "notes": f"Conteo semanal: {notes}",
                "movement_type": "count"
            }
            
            await db.stock_movements.insert_one(movement)
            
            # Update stock
            await db.inventory.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {
                    "current_stock": counted_stock,
                    "last_count": datetime.utcnow(),
                    "last_counted_by": user["username"]
                }}
            )

            # Check if item needs reordering
            if counted_stock <= float(item.get("min_stock", 0)):
                items_below_min.append(item_id)

        # Create order suggestions document if items need reordering
        if items_below_min:
            await db.order_suggestions.insert_one({
                "created_at": datetime.utcnow(),
                "created_by": user["username"],
                "source": "weekly_count",
                "items": items_below_min,
                "status": "pending"
            })
        
        return JSONResponse({
            "success": True,
            "message": "Weekly count recorded successfully",
            "items_below_min": len(items_below_min),
            "suggestions_created": bool(items_below_min)
        })
        
    except Exception as e:
        logger.error(f"Error in weekly count: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/inventory/search")
async def search_inventory_items(request: Request, q: str):
    """Search inventory items for autocomplete"""
    try:
        db = await get_db()
        query = {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"supplier": {"$regex": q, "$options": "i"}},
                {"category": {"$regex": q, "$options": "i"}}
            ]
        }
        
        items = await db.inventory.find(query).limit(10).to_list(None)
        
        # Format results for autocomplete
        results = [{
            "id": str(item["_id"]),
            "name": item["name"],
            "supplier": item["supplier"],
            "category": item["category"],
            "current_stock": item["current_stock"],
            "unit": item["unit"]
        } for item in items]
        
        return results
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
# Add this new route
@router.get("/api/inventory/categories")
async def get_categories(request: Request):
    """Get all available categories"""
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=403, detail="Not authenticated")

        db = await get_db()
        
        # Combine default categories with any custom ones from the database
        existing_categories = await db.inventory.distinct("category")
        all_categories = list(set(filter(None, existing_categories + DEFAULT_CATEGORIES)))
        
        return {
            "categories": sorted(all_categories),
            "default_categories": sorted(DEFAULT_CATEGORIES)
        }
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this route to update an item's category
@router.patch("/api/inventory/{item_id}/category")
async def update_category(item_id: str, request: Request):
    """Update an item's category"""
    try:
        # Check user authentication and admin status
        user = request.state.user
        if not user or not user.get('is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Get request body
        body = await request.json()
        new_category = body.get("category")
        
        if not new_category:
            raise HTTPException(status_code=400, detail="Category is required")

        db = await get_db()
        
        # Get current item for logging
        current_item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not current_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Update the category
        result = await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "category": new_category,
                "last_updated": datetime.utcnow(),
                "last_updated_by": user["username"]
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item not found or category unchanged")

        # Log the category change
        logger.info(
            f"Category updated for item {current_item['name']} "
            f"from '{current_item.get('category', 'None')}' to '{new_category}' "
            f"by {user['username']}"
        )

        return {
            "success": True,
            "item_id": str(item_id),
            "category": new_category,
            "message": "Category updated successfully"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inventory/{item_id}/movement")
async def record_stock_movement(
    item_id: str,
    request: Request,
    movement: StockMovement
):
    try:
        user = request.state.user
        db = await get_db()
        
        # Get current item
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Regular users can only add stock
        if not user.get("is_admin") and movement.movement_type != "add":
            raise HTTPException(status_code=403, detail="Only admins can reduce stock")

        # Calculate new stock
        current_stock = item.get("current_stock", 0)
        quantity = abs(float(movement.quantity))
        
        if movement.movement_type == "subtract":
            if not user.get("is_admin"):
                raise HTTPException(status_code=403, detail="Unauthorized")
            quantity = -quantity

        new_stock = current_stock + quantity

        # Record movement
        movement_record = {
            "item_id": ObjectId(item_id),
            "item_name": item["name"],
            "user_id": ObjectId(user["_id"]),
            "username": user["username"],
            "quantity": quantity,
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "timestamp": datetime.utcnow(),
            "notes": movement.notes,
            "movement_type": movement.movement_type
        }

        # Insert movement record
        await db.stock_movements.insert_one(movement_record)
        
        # Update item stock
        await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {
                "$set": {
                    "current_stock": new_stock,
                    "last_updated": datetime.utcnow(),
                    "last_updated_by": user["username"]
                }
            }
        )

        # Prepare serialized response
        serialized_movement = {
            "item_id": str(movement_record["item_id"]),
            "item_name": movement_record["item_name"],
            "user_id": str(movement_record["user_id"]),
            "username": movement_record["username"],
            "quantity": movement_record["quantity"],
            "previous_stock": movement_record["previous_stock"],
            "new_stock": movement_record["new_stock"],
            "timestamp": movement_record["timestamp"].isoformat(),
            "notes": movement_record["notes"],
            "movement_type": movement_record["movement_type"]
        }

        return JSONResponse({
            "success": True,
            "new_stock": new_stock,
            "movement": serialized_movement
        })

    except Exception as e:
        logger.error(f"Error recording stock movement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/inventory/{item_id}/movements")
async def get_item_movements(item_id: str, request: Request):
    """Get movement history for an item"""
    try:
        user = request.state.user
        db = await get_db()
        
        # Convert string ID to ObjectId for query
        object_id = ObjectId(item_id)
        
        query = {"item_id": object_id}
        if not user.get("is_admin"):
            query["user_id"] = ObjectId(user["_id"])

        movements = await db.stock_movements.find(query).sort("timestamp", -1).to_list(None)
        
        # Convert ObjectIds to strings in the response
        for movement in movements:
            movement["_id"] = str(movement["_id"])
            movement["item_id"] = str(movement["item_id"])
            movement["user_id"] = str(movement["user_id"])
            # Convert datetime to ISO format string
            movement["timestamp"] = movement["timestamp"].isoformat()
        
        return movements

    except Exception as e:
        logger.error(f"Error getting movements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inventory/{item_id}/set-stock")
async def set_stock(item_id: str, request: Request):
    """Set absolute stock value for an item"""
    try:
        user = request.state.user
        if not user or not user.get('is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")
            
        body = await request.json()
        new_stock = float(body.get("new_stock", 0))
        notes = body.get("notes")
        
        db = await get_db()
        
        # Get current item
        item = await db.inventory.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        current_stock = item.get("current_stock", 0)
        stock_difference = new_stock - current_stock

        # Record movement
        movement = {
            "item_id": ObjectId(item_id),
            "item_name": item["name"],
            "user_id": ObjectId(user["_id"]),
            "username": user["username"],
            "quantity": stock_difference,
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "timestamp": datetime.utcnow(),
            "notes": f"Ajuste manual: {notes}",
            "movement_type": "set"
        }
        
        await db.stock_movements.insert_one(movement)
        
        # Update stock
        await db.inventory.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "current_stock": new_stock,
                "last_updated": datetime.utcnow(),
                "last_updated_by": user["username"]
            }}
        )

        return {
            "success": True,
            "new_stock": new_stock,
            "difference": stock_difference
        }
        
    except Exception as e:
        logger.error(f"Error setting stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))