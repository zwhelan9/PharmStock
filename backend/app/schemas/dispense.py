from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class DispenseRequest(BaseModel):
    medicine_id: int
    quantity: int
    prescription_ref: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Dispense quantity must be at least 1")
        return v


class DispenseLineItemRead(BaseModel):
    id: int
    pack_instance_id: int
    quantity_deducted: int
    pack_status_after: str

    model_config = {"from_attributes": True}


class DispenseTransactionRead(BaseModel):
    id: int
    medicine_id: int
    total_quantity: int
    source: str
    touchstore_ref: Optional[str]
    prescription_ref: Optional[str]
    served_by_user_id: Optional[int]
    notes: Optional[str]
    dispense_date: Optional[datetime]
    created_at: Optional[datetime]
    line_items: List[DispenseLineItemRead] = []
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}
