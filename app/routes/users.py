from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..models.user import User, UserDisplay
from ..database import db
from ..auth import get_password_hash

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/users")
async def users_list(request: Request):
    if not request.session.get("user") or not request.session.get("is_admin"):
        return RedirectResponse(url="/login")
    
    users = await db.users.find({}, {"password": 0}).to_list(None)
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users,
            "is_admin": True
        }
    )

@router.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    existing_user = await db.users.find_one({"username": username})
    if existing_user:
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "error": "Username already exists",
                "users": await db.users.find({}, {"password": 0}).to_list(None),
                "is_admin": True
            }
        )

    user_data = {
        "username": username,
        "password": get_password_hash(password),
        "role": role
    }
    await db.users.insert_one(user_data)
    return RedirectResponse(url="/users", status_code=303)

@router.post("/users/delete/{username}")
async def delete_user(request: Request, username: str):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    await db.users.delete_one({"username": username})
    return RedirectResponse(url="/users", status_code=303)