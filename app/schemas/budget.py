from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BudgetItemCreate(BaseModel):
    item_id: Optional[int] = None  # opcional: del banco de servicios
    description: str
    quantity: float = 1.0
    unit_price: float


class BudgetItemResponse(BaseModel):
    id: int
    budget_id: int
    item_id: Optional[int] = None
    description: str
    quantity: float
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    client_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    discount_percent: float = 0.0
    tax_percent: float = 0.0
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    work_timeline: Optional[str] = None
    valid_until: Optional[datetime] = None
    items: List[BudgetItemCreate] = []


class BudgetUpdate(BaseModel):
    client_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # pending, accepted, rejected
    tax_percent: Optional[float] = None
    notes: Optional[str] = None
    valid_until: Optional[datetime] = None


class BudgetResponse(BaseModel):
    id: int
    user_id: int
    client_id: Optional[int] = None
    number: int
    title: str
    description: Optional[str] = None
    status: str
    subtotal: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    tax_percent: float
    tax_amount: float
    total: float
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    work_timeline: Optional[str] = None
    valid_until: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    budget_items: List[BudgetItemResponse] = []

    model_config = {"from_attributes": True}
