from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class TouchStoreImport(BaseModel):
    """Payload representing a dispense event from TouchStore Rx."""
    product_id: int  # medicine_id in our system
    quantity: int
    touchstore_ref: Optional[str] = None
    prescription_ref: Optional[str] = None
    dispense_timestamp: Optional[datetime] = None

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Dispense quantity must be at least 1")
        return v


class ReconciliationFlag(BaseModel):
    medicine_id: int
    medicine_name: str
    system_on_hand: int
    touchstore_reported: Optional[int]
    discrepancy: int


class ReconciliationRequest(BaseModel):
    reason: str
    touchstore_reported: Optional[int] = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Reason is required (at least 1 character)")
        return v.strip()


class ReconciliationRead(BaseModel):
    id: int
    medicine_id: int
    quantity_before: int
    quantity_after: int
    reason: str
    adjusted_by_user_id: int
    touchstore_reported: Optional[int]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}
