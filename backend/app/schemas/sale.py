from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SaleCreate(BaseModel):
    medicine_id: int
    batch_id: Optional[int] = None
    quantity: int = Field(..., ge=1)
    unit_price: Optional[float] = Field(None, ge=0)
    customer_ref: Optional[str] = None
    prescription_ref: Optional[str] = None
    is_prescription: bool = False
    served_by: Optional[str] = None
    notes: Optional[str] = None
    sale_date: Optional[datetime] = None


class SaleRead(BaseModel):
    id: int
    medicine_id: int
    batch_id: Optional[int] = None
    quantity: int
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    customer_ref: Optional[str] = None
    prescription_ref: Optional[str] = None
    is_prescription: bool
    served_by: Optional[str] = None
    notes: Optional[str] = None
    sale_date: datetime
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}
