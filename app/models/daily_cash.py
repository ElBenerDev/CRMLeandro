from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DailyCash(BaseModel):
    date: datetime
    initial_amount: float = 200.00  # Caja inicial
    billing: Optional[float] = 0  # Facturacion
    expenses: Optional[float] = 0  # Gastos del dia
    details: Optional[str] = None  # Detalle
    safe_amount: Optional[float] = 0  # Caja fuerte - Gastos
    responsible: Optional[str] = None  # Responsable

default_cash_entry = {
    "date": "2025-03-01",
    "initial_cash": 200.00,
    "revenue": 1000.00,
    "expenses": 100.00,
    "details": "",
    "safe_balance": 900.00,
    "responsible": "ONE"
}