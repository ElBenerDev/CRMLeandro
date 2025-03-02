from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserDisplay(BaseModel):
    username: str
    role: str

    class Config:
        from_attributes = True