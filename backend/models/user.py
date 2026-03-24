"""User models / schemas."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class User(BaseModel):
    """Internal user representation."""
    id: str
    name: str
    email: EmailStr
    hashed_password: str
    created_at: datetime
