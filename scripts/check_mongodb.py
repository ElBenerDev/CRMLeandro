from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from pprint import pprint
from collections import defaultdict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def analyze_inventory_data():
    try:
        # Use the same connection string as your main application
        MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
        DATABASE_NAME = os.getenv('DATABASE_NAME', 'crmleandro')  # Update with your actual database name
        
        print(f"Connecting to MongoDB at: {MONGODB_URL}")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        # Test connection
        await client.admin.command('ping')
        print("Successfully connected to MongoDB")
        
        # Get all inventory items
        print("\nFetching inventory items...")
        items = await db.inventory.find({}).to_list(length=None)
        print(f"Found {len(items)} items")
        
        if not items:
            print("No items found in inventory collection")
            return
        
        # Analyze data structure
        field_types = defaultdict(set)
        stock_info = []
        
        for item in items:
            # Check field types
            for field, value in item.items():
                field_types[field].add(type(value).__name__)
            
            # Collect stock information
            stock_info.append({
                'name': item.get('name', 'Unknown'),
                'current_stock': item.get('current_stock', 0),
                'min_stock': item.get('min_stock', 'Not set'),
                'max_stock': item.get('max_stock', 'Not set'),
                'unit': item.get('unit', 'No unit'),
                'supplier': item.get('supplier', 'No supplier')
            })
        
        print("\n=== Field Types ===")
        for field, types in sorted(field_types.items()):
            print(f"{field}: {', '.join(types)}")
        
        print("\n=== Stock Level Analysis ===")
        items_with_min_stock = sum(1 for item in stock_info if item['min_stock'] != 'Not set')
        items_with_max_stock = sum(1 for item in stock_info if item['max_stock'] != 'Not set')
        
        print(f"Items with min_stock: {items_with_min_stock}/{len(items)}")
        print(f"Items with max_stock: {items_with_max_stock}/{len(items)}")
        
        print("\n=== Sample Items with Stock Levels ===")
        for item in sorted(stock_info, key=lambda x: x['name'])[:10]:  # Show first 10 items
            print(f"\nItem: {item['name']}")
            print(f"  Current Stock: {item['current_stock']} {item['unit']}")
            print(f"  Min Stock: {item['min_stock']}")
            print(f"  Max Stock: {item['max_stock']}")
            print(f"  Supplier: {item['supplier']}")
        
        print("\n=== Items Needing Stock Limits ===")
        needs_limits = [item for item in stock_info 
                       if item['min_stock'] == 'Not set' 
                       or item['max_stock'] == 'Not set']
        
        if needs_limits:
            print(f"\nFound {len(needs_limits)} items without stock limits:")
            for item in needs_limits:
                print(f"- {item['name']} ({item['supplier']})")
        else:
            print("All items have stock limits set!")

    except Exception as e:
        print(f"Error analyzing inventory data: {e}")
    finally:
        client.close()
        print("\nConnection closed")

if __name__ == "__main__":
    asyncio.run(analyze_inventory_data())