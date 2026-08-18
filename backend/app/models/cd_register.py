"""
Controlled Drugs Register Models
==================================
Append-only register entries with correction chaining, duty register,
and destruction records with digital witness signature.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey,
    Text, Enum, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class CDTransactionType(str, enum.Enum):
    RECEIPT = "receipt"
    SUPPLY = "supply"


class DutyRole(str, enum.Enum):
    PHARMACIST = "pharmacist"
    SUPERINTENDENT = "superintendent"
    OWNER = "owner"


# ── CD Register Entry ─────────────────────────────────────────────────────────

class CDRegisterEntry(Base):
    __tablename__ = "cd_register_entries"

    id = Column(Integer, primary_key=True, index=True)

    # Transaction details
    transaction_type = Column(Enum(CDTransactionType), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)

    # Product
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    product_strength = Column(String(100), nullable=True)
    product_form = Column(String(100), nullable=True)

    # Quantity and balance
    quantity = Column(Integer, nullable=False)
    running_balance = Column(Integer, nullable=False)

    # Counterparty
    counterparty_name = Column(String(200), nullable=False)
    counterparty_address = Column(Text, nullable=True)

    # Authority / prescription
    authority_reference = Column(String(200), nullable=True)
    prescriber_name = Column(String(200), nullable=True)
    prescriber_reg_number = Column(String(100), nullable=True)

    # Audit
    entered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Correction chain (append-only: corrections reference the original)
    correction_of_entry_id = Column(Integer, ForeignKey("cd_register_entries.id"), nullable=True)
    correction_reason = Column(Text, nullable=True)
    is_correction = Column(Boolean, nullable=False, default=False)
    is_voided = Column(Boolean, nullable=False, default=False)  # True if this entry has been corrected

    # Relationships
    medicine = relationship("Medicine", backref="cd_register_entries")
    entered_by = relationship("User", backref="cd_register_entries")
    correction_of = relationship("CDRegisterEntry", remote_side=[id], backref="corrections")


# ── Duty Register Entry ───────────────────────────────────────────────────────

class DutyRegisterEntry(Base):
    __tablename__ = "duty_register_entries"

    id = Column(Integer, primary_key=True, index=True)

    duty_date = Column(Date, nullable=False, index=True)
    pharmacist_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(DutyRole), nullable=False)

    # Shift details (optional)
    start_time = Column(String(10), nullable=True)  # HH:MM
    end_time = Column(String(10), nullable=True)

    # Audit
    entered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Correction chain
    correction_of_entry_id = Column(Integer, ForeignKey("duty_register_entries.id"), nullable=True)
    correction_reason = Column(Text, nullable=True)
    is_correction = Column(Boolean, nullable=False, default=False)
    is_voided = Column(Boolean, nullable=False, default=False)

    # Relationships
    pharmacist = relationship("User", foreign_keys=[pharmacist_user_id], backref="duty_entries")
    entered_by = relationship("User", foreign_keys=[entered_by_user_id], backref="entered_duty_entries")
    correction_of = relationship("DutyRegisterEntry", remote_side=[id], backref="corrections")


# ── CD Destruction Record ─────────────────────────────────────────────────────

class CDDestructionRecord(Base):
    __tablename__ = "cd_destruction_records"

    id = Column(Integer, primary_key=True, index=True)

    date_of_destruction = Column(Date, nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    quantity_destroyed = Column(Integer, nullable=False)

    # Witness / authentication
    witnessed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    witness_authenticated_at = Column(DateTime(timezone=True), nullable=True)
    digital_signature_hash = Column(String(256), nullable=True)  # SHA-256 of witness confirmation payload

    # Links to register entries being closed out
    linked_register_entry_ids = Column(Text, nullable=True)  # JSON array of CDRegisterEntry IDs

    # Audit
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="cd_destruction_records")
    witnessed_by = relationship("User", foreign_keys=[witnessed_by_user_id], backref="witnessed_destructions")
    created_by = relationship("User", foreign_keys=[created_by_user_id], backref="created_destructions")
