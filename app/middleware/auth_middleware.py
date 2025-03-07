from fastapi import Request
from fastapi.responses import RedirectResponse
from ..database import get_db
from bson import ObjectId  # Add this import
import logging

logger = logging.getLogger(__name__)

# Define route permissions
ADMIN_ONLY_ROUTES = [
    "/users",
    "/dashboard",
    "/daily_cash",
    "/cash_register",
    "/orders",
    "/schedule"
]

# Routes that both admin and regular users can access, but with different permissions
SHARED_ROUTES = [
    "/inventory",
    "/api/inventory"  # Add this to allow API access
]

async def verify_permissions(request: Request, call_next):
    # Public paths that don't require authentication
    public_paths = ["/login", "/static", "/favicon.ico", "/logout"]
    
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    # Check for access token
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
        
    try:
        db = await get_db()
        user = await db.users.find_one({"_id": ObjectId(token)})
        
        if not user:
            logger.warning("No user found for token")
            return RedirectResponse(url="/login", status_code=303)

        # Set complete user state
        request.state.user = {
            "username": user["username"],
            "is_admin": user.get("is_admin", False),
            "permissions": ["view_inventory", "perform_count"] if not user.get("is_admin") else ["all"],
            "_id": str(user["_id"]),
            "role": user.get("role", "user")
        }

        logger.debug(f"User state set: {request.state.user}")

        # Check permissions based on route
        current_path = request.url.path
        is_admin = user.get("is_admin", False)

        # Block non-admins from admin-only routes
        if any(current_path.startswith(route) for route in ADMIN_ONLY_ROUTES):
            if not is_admin:
                logger.warning(f"Non-admin user attempted to access {current_path}")
                return RedirectResponse(url="/inventory", status_code=303)

        # Allow inventory API access for users with perform_count permission
        if (current_path.startswith("/api/inventory") and 
            "perform_count" in request.state.user["permissions"]):
            return await call_next(request)

        # Regular users can only access inventory with limited permissions
        if not is_admin and not any(current_path.startswith(route) for route in SHARED_ROUTES):
            logger.warning(f"User attempted to access unauthorized path {current_path}")
            return RedirectResponse(url="/inventory", status_code=303)

    except Exception as e:
        logger.error(f"Auth middleware error: {str(e)}")
        return RedirectResponse(url="/login", status_code=303)

    return await call_next(request)

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