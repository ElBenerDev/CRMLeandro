from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import logging
from .database import db, get_db  # Remove init_db since it doesn't exist

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG level
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="CRM Leandro")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here"  # Change this in production!
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Import and include routes after app initialization
from .routes import router
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    db = await get_db()
    await db.connect_db()
    # Print all registered routes for debugging
    for route in app.routes:
        logger.info(f"Registered route: {route.path} [{route.name}]")

@app.on_event("shutdown")
async def shutdown_event():
    await db.close_db()

# Root route
@app.get("/")
async def root():
    return {"message": "CRM Leandro API"}