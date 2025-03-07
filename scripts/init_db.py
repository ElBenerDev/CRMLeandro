from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import logging

logger = logging.getLogger(__name__)

def init_database():
    client = MongoClient('mongodb://localhost:27017/')
    db = client.crm_leandro
    
    # Create admin user if not exists
    if db.users.count_documents({'role': 'admin'}) == 0:
        db.users.insert_one({
            'username': 'admin',
            'password_hash': generate_password_hash('admin123'),
            'email': 'admin@example.com',
            'role': 'admin',
            'is_admin': True,
            'permissions': ['all'],
            'created_at': datetime.utcnow()
        })
        print("Admin user created")

    # Create regular user if not exists
    if db.users.count_documents({'role': 'user'}) == 0:
        db.users.insert_one({
            'username': 'user',
            'password_hash': generate_password_hash('user123'),
            'email': 'user@example.com',
            'role': 'user',
            'is_admin': False,
            'permissions': ['view_inventory', 'perform_count'],
            'created_at': datetime.utcnow()
        })
        print("Regular user created")

    # Update all users to ensure correct roles and permissions
    db.users.update_many(
        {'role': 'admin'},
        {'$set': {
            'is_admin': True,
            'permissions': ['all']
        }}
    )
    
    db.users.update_many(
        {'role': 'user'},
        {'$set': {
            'is_admin': False,
            'permissions': ['view_inventory', 'perform_count']
        }}
    )
    print("Updated user roles and permissions")

    # Create count_sessions collection if not exists
    if "count_sessions" not in db.list_collection_names():
        db.create_collection("count_sessions")
        db.count_sessions.create_index([("user_id", 1), ("status", 1)])
        print("Count sessions collection created")

    # Create sample orders
    if db.orders.count_documents({}) == 0:
        sample_orders = [
            {
                'client': 'Client A',
                'description': 'First order sample',
                'amount': 1500.00,
                'status': 'pending',
                'created_at': datetime.utcnow()
            },
            {
                'client': 'Client B',
                'description': 'Second order sample',
                'amount': 2500.00,
                'status': 'completed',
                'created_at': datetime.utcnow() - timedelta(days=1)
            }
        ]
        db.orders.insert_many(sample_orders)
        print("Sample orders created")

    # Create indexes
    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)
    db.orders.create_index('created_at')
    db.orders.create_index([('client', 1), ('status', 1)])
    
    print("Database initialized successfully")

async def init_inventory():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.crm_leandro
    
    try:
        # Check if collections exist
        collections = await db.list_collection_names()
        
        if "inventory" not in collections:
            await db.create_collection("inventory")
        
        if "stock_movements" not in collections:
            await db.create_collection("stock_movements")
        
        # Check if inventory is empty
        if await db.inventory.count_documents({}) == 0:
            # Add sample items
            sample_items = [
                {
                    "name": "Sample Item 1",
                    "current_stock": 100,
                    "unit": "units",
                    "supplier": "Supplier 1",
                    "category": "General",
                    "min_stock": 10,
                    "max_stock": 200,
                    "last_count": None,
                    "created_at": datetime.utcnow()
                },
                {
                    "name": "Sample Item 2",
                    "current_stock": 50,
                    "unit": "kg",
                    "supplier": "Supplier 2",
                    "category": "General",
                    "min_stock": 5,
                    "max_stock": 100,
                    "last_count": None,
                    "created_at": datetime.utcnow()
                }
            ]
            
            await db.inventory.insert_many(sample_items)
            print("Sample inventory items added")
            
        # Create indexes for inventory
        await db.inventory.create_index("name", unique=True)
        await db.inventory.create_index([("supplier", 1), ("category", 1)])
        await db.stock_movements.create_index([("item_id", 1), ("timestamp", -1)])
            
        print("Inventory initialized successfully")
        
    except Exception as e:
        print(f"Error initializing inventory: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    init_database()
    asyncio.run(init_inventory())