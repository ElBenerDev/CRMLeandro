from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class CashEntry(BaseModel):
    date: date
    initial_amount: float = 200.00
    income: float = 0.0
    expenses: float = 0.0
    details: Optional[str] = None
    safe_balance: float
    responsible: str
    created_at: datetime = datetime.now()

class ExpenseDetail(BaseModel):
    description: str
    amount: float
    date: date