from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.routes import router
from app.database import get_db  # Add this import
import logging

logger = logging.getLogger(__name__)
logger.info("Initializing application...")

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add middleware to check authentication
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # List of paths that don't require authentication
    public_paths = [
        "/login",
        "/static",
        "/favicon.ico"
    ]
    
    # Check if path starts with any public path
    is_public = any(
        request.url.path.startswith(path) 
        for path in public_paths
    )
    
    # Allow access to public paths
    if is_public:
        return await call_next(request)

    # Check for access token
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
        
    try:
        # Verify token
        db = await get_db()
        token_exists = await db.active_tokens.find_one({"token": token})
        if not token_exists:
            return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        logger.error(f"Auth middleware error: {str(e)}")
        return RedirectResponse(url="/login", status_code=303)

    return await call_next(request)

# Include all routes
app.include_router(router)

@app.get("/")
async def root(request: Request):
    # Check if user is logged in
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.exception_handler(500)
async def internal_error(request: Request, exc: Exception):
    logger.error(f"Internal error: {str(exc)}")
    return RedirectResponse(url="/login")