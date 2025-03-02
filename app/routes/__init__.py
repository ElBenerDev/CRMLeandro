from fastapi import APIRouter
from . import auth, schedule, daily_cash, users, inventory

router = APIRouter()

# Include all routers with explicit prefixes
router.include_router(auth.router, prefix="")
router.include_router(schedule.router, prefix="")
router.include_router(daily_cash.router, prefix="")
router.include_router(users.router, prefix="")
router.include_router(inventory.router, prefix="")  # This will get the web_router
router.include_router(inventory.api_router)  # This will get the API router