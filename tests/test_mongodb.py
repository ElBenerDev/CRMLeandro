from pymongo import MongoClient
from datetime import datetime

def test_mongodb_connection():
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client.crm_leandro
        
        # Test write operation
        test_doc = {
            "test": True,
            "timestamp": datetime.utcnow()
        }
        result = db.test_collection.insert_one(test_doc)
        print(f"Test document inserted with id: {result.inserted_id}")
        
        # Test read operation
        found_doc = db.test_collection.find_one({"_id": result.inserted_id})
        print(f"Found document: {found_doc}")
        
        # Clean up
        db.test_collection.delete_one({"_id": result.inserted_id})
        print("Test document cleaned up")
        
        return True
    except Exception as e:
        print(f"MongoDB connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_mongodb_connection()