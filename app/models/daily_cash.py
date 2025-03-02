from pydantic import BaseModel
from datetime import date
from typing import Optional

class DailyCash(BaseModel):
    date: date
    initial_cash: float = 200.00
    revenue: float = 0.0
    expenses: float = 0.0
    details: str = ""
    safe_balance: float = 900.00
    responsible: str = ""

default_cash_entry = {
    "date": "2025-03-01",
    "initial_cash": 200.00,
    "revenue": 1000.00,
    "expenses": 100.00,
    "details": "",
    "safe_balance": 900.00,
    "responsible": "ONE"
}