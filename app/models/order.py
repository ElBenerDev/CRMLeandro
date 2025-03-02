from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Order(BaseModel):
    client: str
    description: str
    amount: float
    status: str
    created_at: datetime = datetime.utcnow()
    details: Optional[str] = None