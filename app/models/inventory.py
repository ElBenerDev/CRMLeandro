from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class InventoryItem(BaseModel):
    name: str
    current_stock: float = 0.0
    unit: str
    to_order: Optional[float] = None
    presentation: str
    supplier: str

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