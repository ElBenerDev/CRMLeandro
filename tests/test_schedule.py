from fastapi.testclient import TestClient
from datetime import datetime, time
import pytest
from app.main import app
from app.dependencies import get_current_user

client = TestClient(app)

# Mock admin user for testing
TEST_ADMIN = {
    "username": "testadmin",
    "role": "admin"
}

@pytest.fixture
def mock_admin_user():
    async def override_get_current_user():
        return TEST_ADMIN
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides = {}

def test_create_schedule(mock_admin_user):
    schedule_data = {
        "employee": "John Doe",
        "date": datetime.now().isoformat(),
        "arrival_time": "09:00:00",
        "departure_time": "17:00:00",
        "status": "On time",
        "notes": "Regular shift"
    }
    
    response = client.post("/api/schedule", json=schedule_data)
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"]["employee"] == "John Doe"
    assert "id" in data

def test_get_schedules(mock_admin_user):
    response = client.get("/api/schedule")
    assert response.status_code == 200
    assert isinstance(response.json(), list)