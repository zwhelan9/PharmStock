"""
FEFO (First-Expired-First-Out) Dispensing Service
==================================================
Implements the pack selection algorithm per Requirement 2.

Selection order:
  1. Open packs, ordered by expiry_date ASC, id ASC
  2. Sealed packs, ordered by expiry_date ASC, id ASC (opened on first use)

The service is transactional — if insufficient stock exists, no mutations occur.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.pack_instance import PackInstance, PackStatus
from app.models.dispense_transaction import (
    DispenseTransaction,
    DispenseLineItem,
    DispenseSource,
)


class InsufficientStockError(Exception):
    """Raised when total available stock cannot fulfil a dispense request."""

    def __init__(self, medicine_id: int, requested: int, available: int):
        self.medicine_id = medicine_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for medicine {medicine_id}: "
            f"requested {requested}, available {available}"
        )


class FEFOService:
    """Stateless service — all methods are classmethods operating on a DB session."""

    @classmethod
    def get_on_hand(cls, medicine_id: int, db: Session) -> int:
        """
        Returns on-hand quantity for a medicine:
        SUM(quantity_remaining) for packs with status sealed/open
        and expiry_date >= today.
        """
        today = date.today()
        result = (
            db.query(PackInstance.quantity_remaining)
            .filter(
                PackInstance.medicine_id == medicine_id,
                PackInstance.status.in_([PackStatus.SEALED, PackStatus.OPEN]),
                PackInstance.expiry_date >= today,
            )
            .all()
        )
        return sum(r[0] for r in result)

    @classmethod
    def select_packs(
        cls, medicine_id: int, quantity: int, db: Session
    ) -> List[Tuple[PackInstance, int]]:
        """
        Selects pack instances to fulfil a dispense of `quantity` units.
        Returns list of (pack_instance, qty_to_deduct) tuples.
        Raises InsufficientStockError if not enough stock.

        Does NOT mutate any records — caller is responsible for applying changes.
        """
        if quantity <= 0:
            raise ValueError("Dispense quantity must be positive")

        today = date.today()
        remaining = quantity
        selections: List[Tuple[PackInstance, int]] = []

        # Phase 1: draw from OPEN packs (earliest expiry first, then lowest ID)
        open_packs = (
            db.query(PackInstance)
            .filter(
                PackInstance.medicine_id == medicine_id,
                PackInstance.status == PackStatus.OPEN,
                PackInstance.expiry_date >= today,
                PackInstance.quantity_remaining > 0,
            )
            .order_by(PackInstance.expiry_date.asc(), PackInstance.id.asc())
            .all()
        )

        for pack in open_packs:
            if remaining <= 0:
                break
            take = min(remaining, pack.quantity_remaining)
            selections.append((pack, take))
            remaining -= take

        # Phase 2: draw from SEALED packs (earliest expiry first, then lowest ID)
        if remaining > 0:
            sealed_packs = (
                db.query(PackInstance)
                .filter(
                    PackInstance.medicine_id == medicine_id,
                    PackInstance.status == PackStatus.SEALED,
                    PackInstance.expiry_date >= today,
                    PackInstance.quantity_remaining > 0,
                )
                .order_by(PackInstance.expiry_date.asc(), PackInstance.id.asc())
                .all()
            )

            for pack in sealed_packs:
                if remaining <= 0:
                    break
                take = min(remaining, pack.quantity_remaining)
                selections.append((pack, take))
                remaining -= take

        if remaining > 0:
            available = quantity - remaining
            raise InsufficientStockError(medicine_id, quantity, available)

        return selections

    @classmethod
    def apply_dispense(
        cls,
        medicine_id: int,
        quantity: int,
        db: Session,
        served_by_user_id: Optional[int] = None,
        source: DispenseSource = DispenseSource.MANUAL,
        touchstore_ref: Optional[str] = None,
        prescription_ref: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DispenseTransaction:
        """
        Full dispense operation:
        1. Select packs via FEFO
        2. Create DispenseTransaction
        3. Create DispenseLineItems
        4. Update pack quantities and statuses
        5. Commit

        Raises InsufficientStockError (HTTP 409) if not enough stock.
        """
        selections = cls.select_packs(medicine_id, quantity, db)

        # Create transaction record
        txn = DispenseTransaction(
            medicine_id=medicine_id,
            total_quantity=quantity,
            source=source,
            touchstore_ref=touchstore_ref,
            prescription_ref=prescription_ref,
            served_by_user_id=served_by_user_id,
            notes=notes,
            dispense_date=datetime.now(timezone.utc),
        )
        db.add(txn)
        db.flush()  # get txn.id

        today = date.today()

        for pack, qty_to_deduct in selections:
            # Open sealed pack on first use
            if pack.status == PackStatus.SEALED:
                pack.status = PackStatus.OPEN
                pack.date_opened = today

            pack.quantity_remaining -= qty_to_deduct

            # Determine status after deduction
            if pack.quantity_remaining == 0:
                pack.status = PackStatus.EMPTY
                status_after = "empty"
            else:
                status_after = "open"

            line = DispenseLineItem(
                dispense_transaction_id=txn.id,
                pack_instance_id=pack.id,
                quantity_deducted=qty_to_deduct,
                pack_status_after=status_after,
            )
            db.add(line)

        db.commit()
        db.refresh(txn)
        return txn
