from app import mongo
from app.models.user import User

def init_db():
    """Initialize the database with an admin user if it doesn't exist"""
    if mongo.db.users.count_documents({'role': 'admin'}) == 0:
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')
        admin.save()