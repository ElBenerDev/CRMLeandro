from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from ..utils.json_encoder import mongo_json_dumps
from . import auth

router = APIRouter()

# Include auth router first
router.include_router(auth.router, prefix="", tags=["auth"])

# Import all route modules
from . import main, inventory, schedule, daily_cash, cash_register, orders, users

# Include all routers with proper prefixes matching their route definitions
router.include_router(main.router, prefix="", tags=["main"])
router.include_router(inventory.router, prefix="", tags=["inventory"])
router.include_router(schedule.router, prefix="", tags=["schedule"])
router.include_router(daily_cash.router, prefix="", tags=["daily_cash"])
router.include_router(cash_register.web_router, prefix="", tags=["cash_register"])  # Changed to web_router
router.include_router(orders.router, prefix="", tags=["orders"])
router.include_router(users.router, prefix="/users", tags=["users"])

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["tojson"] = lambda obj: mongo_json_dumps(obj)