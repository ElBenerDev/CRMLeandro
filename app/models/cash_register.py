from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Transaction(BaseModel):
    type: str  # income, expense
    amount: float
    description: str
    time: datetime = Field(default_factory=datetime.now)
    recorded_by: Optional[str] = None

class CashEntry(BaseModel):
    amount: float
    description: str
    type: str  # income, expense
    timestamp: datetime = Field(default_factory=datetime.now)
    recorded_by: Optional[str] = None

class CashRegister(BaseModel):
    date: datetime = Field(default_factory=datetime.now)
    initial_amount: float = Field(default=200.00)
    initial_amount_verified: bool = Field(default=False)
    initial_amount_counted: float = Field(default=0.00)
    initial_count_time: Optional[datetime] = None
    verified_by: Optional[str] = None
    status: str = "open"  # open, closed
    transactions: List[Transaction] = Field(default_factory=list)
    final_count: Optional[float] = None
    final_verification_time: Optional[datetime] = None
    final_verified_by: Optional[str] = None
    notes: Optional[str] = None
    responsible: str
    logs: List[dict] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
    def dict(self, *args, **kwargs):
        """Override dict method to handle datetime serialization"""
        d = super().dict(*args, **kwargs)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                for item in v:
                    for ik, iv in item.items():
                        if isinstance(iv, datetime):
                            item[ik] = iv.isoformat() if iv else None
        return d