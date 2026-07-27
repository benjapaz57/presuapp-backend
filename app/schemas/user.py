from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    business_name: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    business_name: Optional[str] = None
    phone: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pdf_color: Optional[str] = "#4f46e5"
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    business_name: Optional[str] = None
    phone: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pdf_color: Optional[str] = None
