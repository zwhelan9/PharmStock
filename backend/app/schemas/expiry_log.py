from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from app.models.expiry_log import ExpiryAction


class ExpiryLogCreate(BaseModel):
    medicine_id: int
    batch_id: int
    expiry_date: date
    quantity_affected: int = Field(..., ge=1)
    quantity_wasted: Optional[int] = Field(None, ge=0)
    estimated_loss: Optional[float] = Field(None, ge=0)
    action: ExpiryAction
    action_date: date
    performed_by: Optional[str] = None
    notes: Optional[str] = None


class ExpiryLogRead(BaseModel):
    id: int
    medicine_id: int
    batch_id: int
    expiry_date: date
    quantity_affected: int
    quantity_wasted: Optional[int] = None
    estimated_loss: Optional[float] = None
    action: ExpiryAction
    action_date: date
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    medicine_name: Optional[str] = None
    batch_number: Optional[str] = None

    model_config = {"from_attributes": True}
