from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.routes import router
from app.routes.inventory import router as inventory_router  # Add this
from app.middleware.auth_middleware import verify_permissions
from app.database import get_db, init_db
from app.scripts.init_cash_register import init_cash_register
from app.utils.constants import ROLES
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Initializing application...")

# Initialize FastAPI app
app = FastAPI(
    title="CRM Leandro",
    description="Sistema de gestión para Leandro",
    version="1.0.0"
)

# Add session middleware FIRST
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",  # Change this in production!
    session_cookie="session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=False
)

# Add CORS middleware AFTER session
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add auth middleware LAST
app.middleware("http")(verify_permissions)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include all routes
app.include_router(router)
app.include_router(inventory_router)  # Add this

# Make ROLES available globally
app.state.ROLES = ROLES

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Running startup tasks...")
    await init_db()
    await init_cash_register()
    logger.info("Database initialized successfully")

@app.get("/")
async def root(request: Request):
    # Debug logging
    logger.debug("Accessing root path")
    # Check if user is logged in
    token = request.cookies.get("access_token")
    if token:
        logger.debug("Token found, redirecting to dashboard")
        return RedirectResponse(url="/dashboard")
    logger.debug("No token found, redirecting to login")
    return RedirectResponse(url="/login", status_code=303)

@app.exception_handler(500)
async def internal_error(request: Request, exc: Exception):
    logger.error(f"Internal error: {str(exc)}")
    return RedirectResponse(url="/login", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug"
    )