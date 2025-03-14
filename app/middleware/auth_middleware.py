from fastapi import Request
from fastapi.responses import RedirectResponse
from ..database import get_db
from bson import ObjectId  # Add this import
import logging

logger = logging.getLogger(__name__)

# Remove cash register from ADMIN_ONLY_ROUTES
ADMIN_ONLY_ROUTES = [
    "/users",
    "/dashboard",
    "/daily_cash",
    "/orders",
    "/schedule"
]

# Add cash register to SHARED_ROUTES
SHARED_ROUTES = [
    "/inventory",
    "/api/inventory",
    "/cash-register",
    "/api/cash-register"
]

# Add cash register permissions to regular users
USER_PERMISSIONS = {
    "user": [
        "view_inventory",
        "add_stock",
        "search_inventory",
        "sort_inventory",
        "perform_count",
        "view_cash_register",     # Add cash register permission
        "manage_cash_register"    # Add cash register management permission
    ],
    "admin": ["all"]
}

async def verify_permissions(request: Request, call_next):
    # Public paths that don't require authentication
    if request.url.path.startswith(("/login", "/static", "/favicon.ico")):
        return await call_next(request)

    try:
        # Check if user is authenticated via cookie
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login", status_code=303)
            
        # Get user from database
        db = await get_db()
        user = await db.users.find_one({"_id": ObjectId(token)})
        
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        # Set basic user info in request state
        request.state.user = {
            "username": user["username"],
            "is_admin": user["role"] == "admin",
            "role": user["role"]
        }

        return await call_next(request)

    except Exception as e:
        logger.error(f"Auth middleware error: {str(e)}")
        return RedirectResponse(url="/login", status_code=303)

async def check_permissions(request: Request):
    """Check user permissions for the current route"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            return False

        db = await get_db()
        token_data = await db.active_tokens.find_one({"token": token})
        
        if not token_data:
            return False

        user = await db.users.find_one({"_id": ObjectId(token_data["user_id"])})
        
        if not user:
            return False

        # Store user state in request
        request.state.user = {
            "username": user["username"],
            "is_admin": user.get("role") == "admin",
            "permissions": USER_PERMISSIONS.get(user.get("role", "user"), []),
            "_id": str(user["_id"]),
            "role": user.get("role", "user")
        }

        path = request.url.path
        
        # Allow access to shared routes
        if path in SHARED_ROUTES:
            return True
            
        # Admin has access to everything
        if user.get("role") == "admin":
            return True
            
        # Check specific route permissions
        if path.startswith("/cash-register"):
            return "view_cash_register" in request.state.user["permissions"]

        return False

    except Exception as e:
        logger.error(f"Permission check error: {str(e)}")
        return False

from passlib.context import CryptContext
import bcrypt

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # You can adjust the rounds for security/performance
)

async def authenticate_user(username: str, password: str, users_collection):
    user = await users_collection.find_one({"username": username})
    if not user:
        logger.debug(f"User not found: {username}")
        return False
    # Changed from user["hashed_password"] to user["password"]
    if not verify_password(password, user["password"]):
        logger.debug("Invalid password")
        return False
    return user

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)