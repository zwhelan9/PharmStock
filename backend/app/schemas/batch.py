from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class BatchBase(BaseModel):
    medicine_id: int
    batch_number: str = Field(..., min_length=1, max_length=100)
    supplier_invoice: Optional[str] = None
    supplier: Optional[str] = None
    quantity_received: int = Field(..., ge=1)
    quantity_remaining: Optional[int] = None     # defaults to quantity_received if omitted
    cost_price: Optional[float] = Field(None, ge=0)
    purchase_date: date
    manufacture_date: Optional[date] = None
    expiry_date: date
    is_quarantined: bool = False
    notes: Optional[str] = None


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    quantity_remaining: Optional[int] = Field(None, ge=0)
    cost_price: Optional[float] = None
    is_active: Optional[bool] = None
    is_quarantined: Optional[bool] = None
    notes: Optional[str] = None


class BatchRead(BatchBase):
    id: int
    is_active: bool
    days_until_expiry: Optional[int] = None       # computed
    expiry_status: Optional[str] = None           # "critical" | "warning" | "watch" | "ok" | "expired"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
