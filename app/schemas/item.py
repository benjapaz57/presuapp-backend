from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    unit_price: float
    unit: Optional[str] = "unidad"


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[float] = None
    unit: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    unit_price: float
    unit: str
    created_at: datetime

    model_config = {"from_attributes": True}
