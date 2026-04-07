"""User models / schemas."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user password."""
    hashed_password: str


class User(BaseModel):
    """Internal user representation."""
    id: str
    name: str
    email: EmailStr
    hashed_password: str
    created_at: datetime
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None

    class Config:
        # Allow extra fields from database that might not be in the model
        extra = "ignore"
