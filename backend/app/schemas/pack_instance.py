from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class PackInstanceCreate(BaseModel):
    medicine_id: int
    batch_id: Optional[int] = None
    batch_number: str
    lot_number: Optional[str] = None
    expiry_date: date
    quantity_received: int
    unit_cost: Optional[float] = None
    is_controlled_drug: bool = False
    supplier_invoice: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("quantity_received")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity_received must be at least 1")
        return v


class PackInstanceRead(BaseModel):
    id: int
    medicine_id: int
    batch_id: Optional[int]
    batch_number: str
    lot_number: Optional[str]
    expiry_date: date
    quantity_received: int
    quantity_remaining: int
    unit_cost: Optional[float]
    status: str
    date_opened: Optional[date]
    is_controlled_drug: bool
    supplier_invoice: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PackInstanceUpdate(BaseModel):
    notes: Optional[str] = None
    is_controlled_drug: Optional[bool] = None


class OnHandResponse(BaseModel):
    medicine_id: int
    on_hand_quantity: int
