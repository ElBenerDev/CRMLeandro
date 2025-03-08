from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class OrderItem(BaseModel):
    item_id: str
    name: str
    current_stock: float
    min_stock: float
    supplier: str
    unit: str
    suggested_order: float

class Order(BaseModel):
    client: str
    description: str
    amount: float
    status: str
    created_at: datetime = datetime.utcnow()
    details: Optional[str] = None
    items: Optional[List[OrderItem]] = None
    type: str = "manual"  # can be "manual" or "suggestion"