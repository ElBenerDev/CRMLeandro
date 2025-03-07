from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WeeklyCount(BaseModel):
    count_date: datetime
    counted_by: str
    previous_stock: float
    current_stock: float
    difference: float
    notes: Optional[str] = None

class InventoryItem(BaseModel):
    name: str
    current_stock: float = 0.0
    unit: str
    to_order: Optional[float] = None
    presentation: str
    supplier: str
    last_count: Optional[datetime] = None
    weekly_counts: List[WeeklyCount] = []

class ArrivalControl(BaseModel):
    product: str
    quantity: float
    arrival_date: datetime = datetime.now()
    received_by: str

DEFAULT_SUPPLIERS = [
    "ACACIAS", "AMAZON", "CARLOS ROLLOS PACK", "COSTCO", "DEPOT",
    "INSTACAR", "LIZ", "MARIANO", "ROMANO", "SANBER", "SYSCO",
    "TQMUCH", "WALLMART", "WEBRESTAURANT"
]

DEFAULT_ITEMS = [
    {"name": "MILANESAS", "unit": "unidades", "presentation": "CANTIDAD", "supplier": "ACACIAS"},
    {"name": "FRUIT PEBLES (CEREALES)", "unit": "paquetes", "presentation": "PAQUETE", "supplier": "AMAZON"},
    {"name": "OREO", "unit": "cajas", "presentation": "CAJA", "supplier": "AMAZON"},
    # Add more items from the template...
]