from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class CashEntry(BaseModel):
    amount: float
    description: str
    entry_type: str
    timestamp: datetime = datetime.now()
    created_by: Optional[str] = None

class CashRegister(BaseModel):
    opening_amount: float
    closing_amount: Optional[float] = None
    date: datetime = datetime.now()
    entries: List[CashEntry] = []
    status: str = "open"
    created_by: Optional[str] = None
    notes: Optional[str] = None