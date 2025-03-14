from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from .database import db, get_db
from .utils.constants import ROLES
from .middleware.auth_middleware import verify_permissions

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="CRM Leandro")

# Add middlewares in correct order
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here",  # Change this in production!
    same_site="lax",  # Adds security for cookies
    https_only=False  # Set to True in production
)

# Add auth middleware after session middleware
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=verify_permissions
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Import routes
from .routes import router  # Import the main combined router

# Include the main router
app.include_router(router)

# Make ROLES available globally to templates
app.state.ROLES = ROLES

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing application...")
    try:
        db = await get_db()
        await db.connect_db()
        logger.info("Database initialized successfully")
        
        # Print all registered routes for debugging
        for route in app.routes:
            logger.info(f"Registered route: {route.path} [{route.name}]")
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    await db.close_db()
    logger.info("Application shutdown complete")

# Root route redirect to dashboard
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")