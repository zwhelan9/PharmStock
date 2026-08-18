from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class WriteOffCreate(BaseModel):
    pack_instance_id: int
    quantity: int
    reason_code: str
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Write-off quantity must be at least 1")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 500:
            raise ValueError("Notes must be 500 characters or fewer")
        return v


class WriteOffRead(BaseModel):
    id: int
    pack_instance_id: int
    medicine_id: int
    quantity: int
    reason_code: str
    notes: Optional[str]
    calculated_value: Optional[float]
    cost_unavailable: bool
    status: str
    initiated_by_user_id: int
    initiated_at: Optional[datetime]
    countersigned_by_user_id: Optional[int]
    countersigned_at: Optional[datetime]
    countersign_deadline: Optional[datetime]
    created_at: Optional[datetime]
    medicine_name: Optional[str] = None
    initiated_by_username: Optional[str] = None
    countersigned_by_username: Optional[str] = None

    model_config = {"from_attributes": True}


class WriteOffReportRow(BaseModel):
    reason_code: str
    medicine_id: int
    medicine_name: str
    total_quantity: int
    total_value: Optional[float]
    count: int
    cost_unavailable_count: int


class WriteOffReportResponse(BaseModel):
    start_date: str
    end_date: str
    rows: List[WriteOffReportRow]
    grand_total_value: Optional[float]
    grand_total_quantity: int
