"""
Controlled Drugs Register Service
===================================
Append-only entry creation, correction workflow, running balance calculation,
and destruction record sign-off with digital signature hashing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, date, timezone
from typing import Optional, List

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.cd_register import (
    CDRegisterEntry, CDTransactionType,
    DutyRegisterEntry, DutyRole,
    CDDestructionRecord,
)
from app.models.medicine import Medicine
from app.models.user import User


class CDRegisterService:
    """Handles CD register entry creation with running balance and corrections."""

    @classmethod
    def get_running_balance(cls, medicine_id: int, db: Session) -> int:
        """
        Get current running balance for a CD product.
        Based on the most recent non-voided entry for that medicine.
        """
        latest = (
            db.query(CDRegisterEntry)
            .filter(
                CDRegisterEntry.medicine_id == medicine_id,
                CDRegisterEntry.is_voided == False,
            )
            .order_by(CDRegisterEntry.created_at.desc(), CDRegisterEntry.id.desc())
            .first()
        )
        return latest.running_balance if latest else 0

    @classmethod
    def create_entry(
        cls,
        transaction_type: str,
        transaction_date: datetime,
        medicine_id: int,
        quantity: int,
        counterparty_name: str,
        counterparty_address: Optional[str],
        authority_reference: Optional[str],
        prescriber_name: Optional[str],
        prescriber_reg_number: Optional[str],
        user_id: int,
        db: Session,
    ) -> CDRegisterEntry:
        """
        Create a new append-only CD register entry.
        Automatically calculates running balance.
        """
        # Validate medicine
        med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
        if not med:
            raise HTTPException(status_code=404, detail="Medicine not found")

        # Validate transaction type
        try:
            txn_type = CDTransactionType(transaction_type)
        except ValueError:
            raise HTTPException(status_code=422, detail="transaction_type must be 'receipt' or 'supply'")

        if quantity < 1:
            raise HTTPException(status_code=422, detail="Quantity must be at least 1")

        # Calculate running balance
        current_balance = cls.get_running_balance(medicine_id, db)
        if txn_type == CDTransactionType.RECEIPT:
            new_balance = current_balance + quantity
        else:
            new_balance = current_balance - quantity
            if new_balance < 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient CD balance: current {current_balance}, requested supply {quantity}",
                )

        entry = CDRegisterEntry(
            transaction_type=txn_type,
            transaction_date=transaction_date,
            medicine_id=medicine_id,
            product_name=med.name,
            product_strength=med.unit_size,
            product_form=med.unit,
            quantity=quantity,
            running_balance=new_balance,
            counterparty_name=counterparty_name,
            counterparty_address=counterparty_address,
            authority_reference=authority_reference,
            prescriber_name=prescriber_name,
            prescriber_reg_number=prescriber_reg_number,
            entered_by_user_id=user_id,
            is_correction=False,
            is_voided=False,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def correct_entry(
        cls,
        original_entry_id: int,
        correction_reason: str,
        user_id: int,
        db: Session,
        # All corrected fields:
        transaction_type: Optional[str] = None,
        transaction_date: Optional[datetime] = None,
        quantity: Optional[int] = None,
        counterparty_name: Optional[str] = None,
        counterparty_address: Optional[str] = None,
        authority_reference: Optional[str] = None,
        prescriber_name: Optional[str] = None,
        prescriber_reg_number: Optional[str] = None,
    ) -> CDRegisterEntry:
        """
        Create a correction entry linked to the original.
        The original entry is marked as voided but never deleted.
        The correction recalculates the running balance.
        """
        original = db.query(CDRegisterEntry).filter(CDRegisterEntry.id == original_entry_id).first()
        if not original:
            raise HTTPException(status_code=404, detail="Original entry not found")

        if not correction_reason or len(correction_reason.strip()) < 1:
            raise HTTPException(status_code=422, detail="Correction reason is required")

        # Mark original as voided
        original.is_voided = True

        # Build corrected values (use original values where not overridden)
        txn_type_str = transaction_type or original.transaction_type.value
        try:
            txn_type = CDTransactionType(txn_type_str)
        except ValueError:
            raise HTTPException(status_code=422, detail="transaction_type must be 'receipt' or 'supply'")

        corrected_qty = quantity if quantity is not None else original.quantity
        corrected_date = transaction_date or original.transaction_date

        if corrected_qty < 1:
            raise HTTPException(status_code=422, detail="Quantity must be at least 1")

        # Recalculate balance: get balance BEFORE the original entry
        # (find the entry just before the original for this medicine)
        prev_entry = (
            db.query(CDRegisterEntry)
            .filter(
                CDRegisterEntry.medicine_id == original.medicine_id,
                CDRegisterEntry.id < original.id,
                CDRegisterEntry.is_voided == False,
            )
            .order_by(CDRegisterEntry.id.desc())
            .first()
        )
        balance_before = prev_entry.running_balance if prev_entry else 0

        if txn_type == CDTransactionType.RECEIPT:
            new_balance = balance_before + corrected_qty
        else:
            new_balance = balance_before - corrected_qty
            if new_balance < 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Correction would result in negative balance ({new_balance})",
                )

        correction = CDRegisterEntry(
            transaction_type=txn_type,
            transaction_date=corrected_date,
            medicine_id=original.medicine_id,
            product_name=original.product_name,
            product_strength=original.product_strength,
            product_form=original.product_form,
            quantity=corrected_qty,
            running_balance=new_balance,
            counterparty_name=counterparty_name or original.counterparty_name,
            counterparty_address=counterparty_address if counterparty_address is not None else original.counterparty_address,
            authority_reference=authority_reference if authority_reference is not None else original.authority_reference,
            prescriber_name=prescriber_name if prescriber_name is not None else original.prescriber_name,
            prescriber_reg_number=prescriber_reg_number if prescriber_reg_number is not None else original.prescriber_reg_number,
            entered_by_user_id=user_id,
            correction_of_entry_id=original.id,
            correction_reason=correction_reason,
            is_correction=True,
            is_voided=False,
        )
        db.add(correction)
        db.commit()
        db.refresh(correction)
        return correction


class DutyRegisterService:
    """Handles duty register entries with correction support."""

    @classmethod
    def create_entry(
        cls,
        duty_date: date,
        pharmacist_user_id: int,
        role: str,
        entered_by_user_id: int,
        db: Session,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> DutyRegisterEntry:
        # Validate role
        try:
            duty_role = DutyRole(role)
        except ValueError:
            raise HTTPException(status_code=422, detail="role must be 'pharmacist', 'superintendent', or 'owner'")

        # Validate pharmacist user exists
        user = db.query(User).filter(User.id == pharmacist_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Pharmacist user not found")

        entry = DutyRegisterEntry(
            duty_date=duty_date,
            pharmacist_user_id=pharmacist_user_id,
            role=duty_role,
            start_time=start_time,
            end_time=end_time,
            entered_by_user_id=entered_by_user_id,
            is_correction=False,
            is_voided=False,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def correct_entry(
        cls,
        original_id: int,
        correction_reason: str,
        entered_by_user_id: int,
        db: Session,
        duty_date: Optional[date] = None,
        pharmacist_user_id: Optional[int] = None,
        role: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> DutyRegisterEntry:
        original = db.query(DutyRegisterEntry).filter(DutyRegisterEntry.id == original_id).first()
        if not original:
            raise HTTPException(status_code=404, detail="Duty entry not found")

        if not correction_reason or len(correction_reason.strip()) < 1:
            raise HTTPException(status_code=422, detail="Correction reason is required")

        original.is_voided = True

        duty_role = None
        if role:
            try:
                duty_role = DutyRole(role)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid role")

        correction = DutyRegisterEntry(
            duty_date=duty_date or original.duty_date,
            pharmacist_user_id=pharmacist_user_id or original.pharmacist_user_id,
            role=duty_role or original.role,
            start_time=start_time if start_time is not None else original.start_time,
            end_time=end_time if end_time is not None else original.end_time,
            entered_by_user_id=entered_by_user_id,
            correction_of_entry_id=original.id,
            correction_reason=correction_reason,
            is_correction=True,
            is_voided=False,
        )
        db.add(correction)
        db.commit()
        db.refresh(correction)
        return correction


class CDDestructionService:
    """Handles CD destruction with witness authentication and digital signature."""

    @classmethod
    def create_record(
        cls,
        date_of_destruction: date,
        medicine_id: int,
        quantity_destroyed: int,
        witnessed_by_user_id: int,
        witness_password: str,
        linked_register_entry_ids: Optional[List[int]],
        created_by_user_id: int,
        db: Session,
    ) -> CDDestructionRecord:
        """
        Create a destruction record with witness re-authentication.
        The witness must provide their password to sign off (FR-CD-1.4, FR-CD-5.2).
        """
        # Validate medicine
        med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
        if not med:
            raise HTTPException(status_code=404, detail="Medicine not found")

        if quantity_destroyed < 1:
            raise HTTPException(status_code=422, detail="Quantity must be at least 1")

        # Validate witness is a different user
        if witnessed_by_user_id == created_by_user_id:
            raise HTTPException(status_code=403, detail="Witness must be a different user from the creator")

        # Re-authenticate witness (FR-CD-1.4)
        from app.core.security import verify_password
        witness = db.query(User).filter(User.id == witnessed_by_user_id).first()
        if not witness:
            raise HTTPException(status_code=404, detail="Witness user not found")
        if not verify_password(witness_password, witness.hashed_password):
            raise HTTPException(status_code=401, detail="Witness authentication failed — incorrect password")

        # Generate digital signature hash
        now = datetime.now(timezone.utc)
        sig_payload = json.dumps({
            "witness_user_id": witnessed_by_user_id,
            "medicine_id": medicine_id,
            "quantity": quantity_destroyed,
            "date": str(date_of_destruction),
            "timestamp": now.isoformat(),
        }, sort_keys=True)
        signature_hash = hashlib.sha256(sig_payload.encode()).hexdigest()

        # Store linked entry IDs as JSON
        linked_ids_json = json.dumps(linked_register_entry_ids) if linked_register_entry_ids else None

        record = CDDestructionRecord(
            date_of_destruction=date_of_destruction,
            medicine_id=medicine_id,
            product_name=med.name,
            quantity_destroyed=quantity_destroyed,
            witnessed_by_user_id=witnessed_by_user_id,
            witness_authenticated_at=now,
            digital_signature_hash=signature_hash,
            linked_register_entry_ids=linked_ids_json,
            created_by_user_id=created_by_user_id,
        )
        db.add(record)

        # Deduct from CD running balance
        current_balance = CDRegisterService.get_running_balance(medicine_id, db)
        new_balance = current_balance - quantity_destroyed
        if new_balance < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Destruction quantity ({quantity_destroyed}) exceeds CD balance ({current_balance})",
            )

        # Create a supply-type register entry to reflect the destruction
        destruction_entry = CDRegisterEntry(
            transaction_type=CDTransactionType.SUPPLY,
            transaction_date=now,
            medicine_id=medicine_id,
            product_name=med.name,
            product_strength=med.unit_size,
            product_form=med.unit,
            quantity=quantity_destroyed,
            running_balance=new_balance,
            counterparty_name="DESTRUCTION",
            counterparty_address=None,
            authority_reference=f"Destruction Record #{record.id if record.id else 'pending'}",
            entered_by_user_id=created_by_user_id,
            is_correction=False,
            is_voided=False,
        )
        db.add(destruction_entry)

        db.commit()
        db.refresh(record)
        return record
