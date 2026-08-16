from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.stock_log import ChangeType


class StockLogCreate(BaseModel):
    medicine_id: int
    batch_id: Optional[int] = None
    change_type: ChangeType
    quantity: int = Field(..., description="Positive = added, negative = removed")
    reference: Optional[str] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    log_date: Optional[datetime] = None


class StockLogRead(BaseModel):
    id: int
    medicine_id: int
    batch_id: Optional[int] = None
    change_type: ChangeType
    quantity: int
    stock_before: Optional[int] = None
    stock_after: Optional[int] = None
    reference: Optional[str] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    log_date: datetime
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}
