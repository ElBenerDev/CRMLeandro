from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from ..database import get_db
from ..utils.constants import ROLES
from datetime import datetime
import logging
from passlib.hash import bcrypt

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def list_users(request: Request):
    if not request.state.user or not request.state.user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    try:
        db = await get_db()
        users_list = await db.users.find({}, {"password": 0}).to_list(None)
        
        # Convert ObjectId to string for each user
        for user in users_list:
            user["_id"] = str(user["_id"])
            # Ensure role is either admin or user
            if user.get("role") not in ["admin", "user"]:
                user["role"] = "user"
        
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "users": users_list,
                "roles": ROLES,
                "is_admin": request.state.user.get("is_admin", False),
                "current_user": request.state.user
            }
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "error": str(e),
                "roles": ROLES,
                "users": [],
                "is_admin": request.state.user.get("is_admin", False),
                "current_user": request.state.user
            }
        )

@router.post("/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(None),
    role: str = Form(...)
):
    if not request.state.user or not request.state.user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Force role to be either admin or user
    role = "admin" if role == "admin" else "user"
    
    try:
        db = await get_db()
        # Check if user exists
        if await db.users.find_one({"username": username}):
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Hash password
        hashed_password = bcrypt.hash(password)
        
        # Create user with simplified permissions
        user_data = {
            "username": username,
            "password": hashed_password,
            "email": email,
            "role": role,
            "permissions": ["all"] if role == "admin" else ["basic"],
            "is_admin": role == "admin",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        result = await db.users.insert_one(user_data)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
        return RedirectResponse(url="/users", status_code=303)
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete/{username}")
async def delete_user(request: Request, username: str):
    if not request.state.user or not request.state.user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    try:
        db = await get_db()
        result = await db.users.delete_one({"username": username})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))