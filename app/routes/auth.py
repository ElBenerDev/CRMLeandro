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
from ..database import db
from ..auth import authenticate_user, get_password_hash
from starlette.middleware.sessions import SessionMiddleware
import logging
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()

# Set up password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/token")
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

@router.post("/login")
async def login(request: Request):
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        logger.debug(f"Login attempt for user: {username}")
        
        user = await db.users.find_one({"username": username})
        
        if user and pwd_context.verify(password, user["password"]):
            logger.debug("Password verified successfully")
            request.session["user"] = username
            request.session["is_admin"] = user.get("role") == "admin"
            return RedirectResponse(url="/dashboard", status_code=303)
        
        logger.warning(f"Failed login attempt for user: {username}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@router.get("/dashboard")
async def dashboard(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": request.session.get("user"),
        "is_admin": request.session.get("is_admin", False)
    })

# Add this route temporarily to check database users
@router.get("/debug/users")
async def debug_users():
    try:
        users = await db.users.find().to_list(length=10)
        return {"users": [{"username": u["username"]} for u in users]}
    except Exception as e:
        return {"error": str(e)}