from pydantic import BaseModel, EmailStr
from typing import Optional, List

class User(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: str = "user"
    permissions: List[str] = ["basic"]
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: str = "user"

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

class UserDisplay(BaseModel):
    username: str
    email: Optional[EmailStr]
    role: str
    permissions: List[str]
    is_active: bool
    last_login: Optional[str]

    class Config:
        from_attributes = True