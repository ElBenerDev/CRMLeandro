from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from ..dependencies import (
    get_user,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..database import get_db, db
from ..auth import authenticate_user, get_password_hash
from starlette.middleware.sessions import SessionMiddleware
import logging
from passlib.context import CryptContext
import secrets

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
web_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@web_router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await User.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@web_router.get("/login", name="auth.login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", 
        {"request": request}
    )

@web_router.post("/login", name="auth.login_post")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        db = await get_db()
        user = await db.users.find_one({"username": username})
        
        if not user or not pwd_context.verify(password, user["password"]):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid credentials"},
                status_code=400
            )

        # Generate token
        token = secrets.token_urlsafe(32)
        
        # Store token in database
        await db.active_tokens.insert_one({
            "token": token,
            "username": username,
            "is_admin": user.get("is_admin", False)
        })
        
        # Create response with token cookie
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=3600,  # 1 hour
            path="/"
        )
        
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Login failed"},
            status_code=400
        )

@web_router.get("/logout", name="auth.logout")
async def logout(request: Request):
    try:
        # Remove token from database
        db = await get_db()
        token = request.cookies.get("access_token")
        if token:
            await db.active_tokens.delete_one({"token": token})
        
        # Create response that clears cookie
        response = RedirectResponse(url="/login")
        response.delete_cookie(key="access_token", path="/")
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return RedirectResponse(url="/login")

@web_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@web_router.get("/dashboard")
async def dashboard(request: Request):
    try:
        db = await get_db()
        stats = {
            "total_users": await db.users.count_documents({}),
            "total_orders": await db.orders.count_documents({}),
            "total_inventory": await db.inventory.count_documents({})
        }
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "stats": stats}
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this route temporarily to check database users
@web_router.get("/debug/users")
async def debug_users():
    try:
        users = await db.users.find().to_list(length=10)
        return {"users": [{"username": u["username"]} for u in users]}
    except Exception as e:
        return {"error": str(e)}

# Export the router
router = web_router