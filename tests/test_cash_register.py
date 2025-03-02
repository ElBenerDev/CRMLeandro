from fastapi.testclient import TestClient
from datetime import datetime
import pytest
from ..app.main import app
from ..app.dependencies import get_current_user

client = TestClient(app)

# Mock user for testing
TEST_USER = {
    "username": "testuser",
    "role": "admin"
}

@pytest.fixture
def mock_user():
    async def override_get_current_user():
        return TEST_USER
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides = {}

def test_create_cash_entry(mock_user):
    entry_data = {
        "date": datetime.now().isoformat(),
        "initial_cash": 200.00,
        "income": 1000.00,
        "expenses": 100.00,
        "details": "Test entry",
        "safe_balance": 1100.00,
        "responsible": "TEST"
    }
    
    response = client.post("/api/cash-register/", json=entry_data)
    assert response.status_code == 200
    data = response.json()
    assert data["initial_cash"] == 200.00
    assert data["income"] == 1000.00
    assert "created_by" in data

def test_get_cash_entries(mock_user):
    response = client.get("/api/cash-register/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_cash_entry(mock_user):
    # First create an entry
    entry_data = {
        "date": datetime.now().isoformat(),
        "initial_cash": 200.00,
        "income": 1000.00,
        "expenses": 100.00,
        "details": "Test entry",
        "safe_balance": 1100.00,
        "responsible": "TEST"
    }
    
    create_response = client.post("/api/cash-register/", json=entry_data)
    entry_id = create_response.json()["_id"]
    
    # Update the entry
    update_data = {
        "income": 1500.00,
        "safe_balance": 1600.00
    }
    
    response = client.put(f"/api/cash-register/{entry_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["income"] == 1500.00
    assert data["safe_balance"] == 1600.00

def test_delete_cash_entry(mock_user):
    # First create an entry
    entry_data = {
        "date": datetime.now().isoformat(),
        "initial_cash": 200.00,
        "income": 1000.00,
        "expenses": 100.00,
        "details": "Test entry",
        "safe_balance": 1100.00,
        "responsible": "TEST"
    }
    
    create_response = client.post("/api/cash-register/", json=entry_data)
    entry_id = create_response.json()["_id"]
    
    # Delete the entry
    response = client.delete(f"/api/cash-register/{entry_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f"/api/cash-register/{entry_id}")
    assert get_response.status_code == 404