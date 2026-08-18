"""
Write-Off Service
==================
Handles write-off creation, validation, and controlled-drug countersign workflow.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.pack_instance import PackInstance, PackStatus
from app.models.write_off import WriteOff, ReasonCode, WriteOffStatus
from app.models.user import User


class WriteOffService:

    @classmethod
    def create(
        cls,
        pack_instance_id: int,
        quantity: int,
        reason_code: str,
        notes: Optional[str],
        user_id: int,
        db: Session,
    ) -> WriteOff:
        """
        Create a write-off. For controlled drugs, the write-off is placed in
        'pending_countersign' state. For others, it is finalised immediately
        and the pack quantity is deducted.
        """
        # Validate pack instance
        pack = db.query(PackInstance).filter(PackInstance.id == pack_instance_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="Pack instance not found")

        if pack.status == PackStatus.EMPTY:
            raise HTTPException(status_code=400, detail="Pack is empty — cannot write off")

        # Validate quantity
        if quantity < 1:
            raise HTTPException(status_code=422, detail="Write-off quantity must be at least 1")
        if quantity > pack.quantity_remaining:
            raise HTTPException(
                status_code=422,
                detail=f"Write-off quantity ({quantity}) exceeds available stock ({pack.quantity_remaining})",
            )

        # Validate reason code
        try:
            reason = ReasonCode(reason_code)
        except ValueError:
            valid = [r.value for r in ReasonCode]
            raise HTTPException(
                status_code=422,
                detail=f"Invalid reason_code '{reason_code}'. Must be one of: {valid}",
            )

        # Validate notes length
        if notes and len(notes) > 500:
            raise HTTPException(status_code=422, detail="Notes must be 500 characters or fewer")

        # Calculate value
        calculated_value = None
        cost_unavailable = False
        if pack.unit_cost is not None:
            calculated_value = round(quantity * pack.unit_cost, 2)
        else:
            cost_unavailable = True

        # Determine status based on controlled drug flag
        now = datetime.now(timezone.utc)
        is_controlled = pack.is_controlled_drug

        if is_controlled:
            wo_status = WriteOffStatus.PENDING_COUNTERSIGN
            deadline = now + timedelta(hours=settings.COUNTERSIGN_WINDOW_HOURS)
        else:
            wo_status = WriteOffStatus.FINALISED
            deadline = None

        wo = WriteOff(
            pack_instance_id=pack.id,
            medicine_id=pack.medicine_id,
            quantity=quantity,
            reason_code=reason,
            notes=notes,
            calculated_value=calculated_value,
            cost_unavailable=cost_unavailable,
            status=wo_status,
            initiated_by_user_id=user_id,
            initiated_at=now,
            countersign_deadline=deadline,
        )
        db.add(wo)

        # For non-controlled drugs, deduct immediately
        if not is_controlled:
            cls._apply_deduction(pack, quantity)

        db.commit()
        db.refresh(wo)
        return wo

    @classmethod
    def countersign(
        cls,
        writeoff_id: int,
        countersigner_user_id: int,
        db: Session,
    ) -> WriteOff:
        """
        Countersign a pending controlled-drug write-off.
        Validates that countersigner is different from initiator and holds
        a pharmacist/admin/staff role.
        """
        wo = db.query(WriteOff).filter(WriteOff.id == writeoff_id).first()
        if not wo:
            raise HTTPException(status_code=404, detail="Write-off not found")

        if wo.status != WriteOffStatus.PENDING_COUNTERSIGN:
            raise HTTPException(status_code=400, detail="Write-off is not pending countersign")

        if countersigner_user_id == wo.initiated_by_user_id:
            raise HTTPException(
                status_code=403,
                detail="Initiating user cannot countersign their own write-off",
            )

        # Validate countersigner role
        user = db.query(User).filter(User.id == countersigner_user_id).first()
        if not user or user.role not in ("admin", "staff"):
            raise HTTPException(
                status_code=403,
                detail="Countersigner must hold a Pharmacist/Staff or Admin role",
            )

        # Finalise
        now = datetime.now(timezone.utc)
        wo.status = WriteOffStatus.FINALISED
        wo.countersigned_by_user_id = countersigner_user_id
        wo.countersigned_at = now

        # Apply deduction now
        pack = db.query(PackInstance).filter(PackInstance.id == wo.pack_instance_id).first()
        if pack.quantity_remaining < wo.quantity:
            raise HTTPException(
                status_code=409,
                detail="Pack quantity changed since write-off was initiated — insufficient stock",
            )
        cls._apply_deduction(pack, wo.quantity)

        db.commit()
        db.refresh(wo)
        return wo

    @staticmethod
    def _apply_deduction(pack: PackInstance, quantity: int) -> None:
        """Deduct quantity from pack and update status per Req 1 rules."""
        pack.quantity_remaining -= quantity
        if pack.quantity_remaining == 0:
            pack.status = PackStatus.EMPTY
        elif pack.status == PackStatus.SEALED:
            from datetime import date as date_type
            pack.status = PackStatus.OPEN
            pack.date_opened = date_type.today()
