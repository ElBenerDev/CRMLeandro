from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default stock limits by supplier
SUPPLIER_LIMITS = {
    'ACACIAS': {'min': 5, 'max': 30},
    'AMAZON': {'min': 5, 'max': 30},
    'COSTCO': {'min': 3, 'max': 15},
    'SYSCO': {'min': 2, 'max': 10},
    'SANBER': {'min': 3, 'max': 15},
    'CLEANING_SUPPLIES': {'min': 2, 'max': 8},
    'ICE_CREAM': {'min': 5, 'max': 20},
    'PACKAGING': {'min': 2, 'max': 10},
    'EQUIPMENT': {'min': 1, 'max': 3},
    'MAINTENANCE': {'min': 1, 'max': 2},
    'FOOD_SUPPLIER': {'min': 5, 'max': 25},
    'CONDIMENTS': {'min': 3, 'max': 15},
    'BASIC_SUPPLIES': {'min': 2, 'max': 10}
}

# Default fallback values
DEFAULT_MIN_STOCK = 5
DEFAULT_MAX_STOCK = 30

async def update_stock_limits():
    try:
        MONGODB_URL = os.getenv('MONGODB_URL')
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.crm_leandro
        
        print("Updating stock limits...")
        count = 0
        
        async for item in db.inventory.find({}):
            supplier = item.get('supplier')
            limits = SUPPLIER_LIMITS.get(supplier, {'min': DEFAULT_MIN_STOCK, 'max': DEFAULT_MAX_STOCK})
            
            await db.inventory.update_one(
                {'_id': item['_id']},
                {'$set': {
                    'min_stock': item.get('min_stock', limits['min']),
                    'max_stock': item.get('max_stock', limits['max'])
                }}
            )
            count += 1
            print(f"Updated {item['name']} - Min: {limits['min']}, Max: {limits['max']}")
        
        print(f"\nUpdated {count} items with stock limits")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("\nConnection closed")

if __name__ == "__main__":
    asyncio.run(update_stock_limits())