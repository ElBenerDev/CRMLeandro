from fastapi import APIRouter
from . import auth  # Make sure this import is present

router = APIRouter()

# Include auth router first
router.include_router(auth.router, prefix="", tags=["auth"])

# Import all route modules
from . import main, inventory, schedule, daily_cash, cash_register, orders, users

# Include all routers with explicit prefixes and names
router.include_router(main.router, prefix="", tags=["main"])
router.include_router(inventory.router, prefix="", tags=["inventory"])
router.include_router(schedule.router, prefix="", tags=["schedule"])
router.include_router(daily_cash.router, prefix="", tags=["daily_cash"])
router.include_router(cash_register.router, prefix="", tags=["cash_register"])
router.include_router(orders.router, prefix="", tags=["orders"])
router.include_router(users.router, prefix="", tags=["users"])