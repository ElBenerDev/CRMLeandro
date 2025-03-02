from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

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
            'created_at': datetime.utcnow()
        })
        print("Regular user created")

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
            # Add some sample items
            sample_items = [
                {
                    "name": "Sample Item 1",
                    "current_stock": 100,
                    "unit": "units",
                    "supplier": "Supplier 1",
                    "created_at": datetime.utcnow()
                },
                # Add more sample items as needed
            ]
            
            await db.inventory.insert_many(sample_items)
            print("Sample inventory items added")
            
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    init_database()
    asyncio.run(init_inventory())