from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.routes import (
    auth,
    main,
    inventory,
    schedule,
    daily_cash,
    cash_register,
    orders,
    users
)
from app.database import init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include all routers
app.include_router(auth.router)
app.include_router(main.router)
app.include_router(inventory.router)
app.include_router(schedule.router)
app.include_router(daily_cash.router)
app.include_router(cash_register.router)
app.include_router(orders.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/login")

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing application...")
    await init_db()