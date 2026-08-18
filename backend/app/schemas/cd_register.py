from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime


# ── CD Register Entry ─────────────────────────────────────────────────────────

class CDRegisterEntryCreate(BaseModel):
    transaction_type: str  # receipt | supply
    transaction_date: datetime
    medicine_id: int
    quantity: int
    counterparty_name: str
    counterparty_address: Optional[str] = None
    authority_reference: Optional[str] = None
    prescriber_name: Optional[str] = None
    prescriber_reg_number: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CDRegisterCorrectionCreate(BaseModel):
    correction_reason: str
    transaction_type: Optional[str] = None
    transaction_date: Optional[datetime] = None
    quantity: Optional[int] = None
    counterparty_name: Optional[str] = None
    counterparty_address: Optional[str] = None
    authority_reference: Optional[str] = None
    prescriber_name: Optional[str] = None
    prescriber_reg_number: Optional[str] = None

    @field_validator("correction_reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Correction reason is required")
        return v.strip()


class CDRegisterEntryRead(BaseModel):
    id: int
    transaction_type: str
    transaction_date: Optional[datetime]
    medicine_id: int
    product_name: str
    product_strength: Optional[str]
    product_form: Optional[str]
    quantity: int
    running_balance: int
    counterparty_name: str
    counterparty_address: Optional[str]
    authority_reference: Optional[str]
    prescriber_name: Optional[str]
    prescriber_reg_number: Optional[str]
    entered_by_user_id: int
    entered_by_username: Optional[str] = None
    created_at: Optional[datetime]
    correction_of_entry_id: Optional[int]
    correction_reason: Optional[str]
    is_correction: bool
    is_voided: bool

    model_config = {"from_attributes": True}


# ── Duty Register ────────────────────────────────────────────────────────────

class DutyRegisterEntryCreate(BaseModel):
    duty_date: date
    pharmacist_user_id: int
    role: str  # pharmacist | superintendent | owner
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class DutyRegisterCorrectionCreate(BaseModel):
    correction_reason: str
    duty_date: Optional[date] = None
    pharmacist_user_id: Optional[int] = None
    role: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    @field_validator("correction_reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Correction reason is required")
        return v.strip()


class DutyRegisterEntryRead(BaseModel):
    id: int
    duty_date: date
    pharmacist_user_id: int
    pharmacist_name: Optional[str] = None
    role: str
    start_time: Optional[str]
    end_time: Optional[str]
    entered_by_user_id: int
    entered_by_username: Optional[str] = None
    created_at: Optional[datetime]
    correction_of_entry_id: Optional[int]
    correction_reason: Optional[str]
    is_correction: bool
    is_voided: bool

    model_config = {"from_attributes": True}


# ── CD Destruction ───────────────────────────────────────────────────────────

class CDDestructionCreate(BaseModel):
    date_of_destruction: date
    medicine_id: int
    quantity_destroyed: int
    witnessed_by_user_id: int
    witness_password: str
    linked_register_entry_ids: Optional[List[int]] = None

    @field_validator("quantity_destroyed")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CDDestructionRead(BaseModel):
    id: int
    date_of_destruction: date
    medicine_id: int
    product_name: str
    quantity_destroyed: int
    witnessed_by_user_id: int
    witness_name: Optional[str] = None
    witness_authenticated_at: Optional[datetime]
    digital_signature_hash: Optional[str]
    linked_register_entry_ids: Optional[str]
    created_by_user_id: int
    created_by_username: Optional[str] = None
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}
