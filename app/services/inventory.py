from datetime import datetime
from typing import Dict, Any
from ..database import get_db
import logging

logger = logging.getLogger(__name__)

async def get_inventory_state(user: Dict[str, Any]) -> Dict[str, bool]:
    """Determine the current inventory state for a user"""
    try:
        db = await get_db()
        
        # Check for active count session
        active_count = await db.count_sessions.find_one({
            "user_id": user.get("_id"),
            "status": "in_progress"
        })

        # For testing: Always allow count for non-admin users
        is_admin = bool(user.get("is_admin", False))
        is_count_day = True  # Force to true for testing
        is_counting = bool(active_count)

        logger.debug(f"""
Inventory State Calculation:
- Username: {user.get('username')}
- Is Admin: {is_admin}
- Is Count Day: {is_count_day}
- Is Counting: {is_counting}
""")

        return {
            "is_admin": is_admin,
            "is_count_day": is_count_day,
            "is_counting": is_counting
        }
    except Exception as e:
        logger.error(f"Error getting inventory state: {str(e)}")
        raise e