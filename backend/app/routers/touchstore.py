"""
TouchStore Rx Integration Router
=================================
Handles import of dispense events from TouchStore Rx,
reconciliation flagging, and manual adjustments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.medicine import Medicine
from app.models.reconciliation_adjustment import ReconciliationAdjustment
from app.models.dispense_transaction import DispenseSource
from app.schemas.touchstore import (
    TouchStoreImport,
    ReconciliationFlag,
    ReconciliationRequest,
    ReconciliationRead,
)
from app.schemas.dispense import DispenseTransactionRead
from app.services.fefo import FEFOService, InsufficientStockError

router = APIRouter(prefix="/touchstore", tags=["TouchStore Rx"])


@router.post("/import", response_model=DispenseTransactionRead, status_code=201)
def import_dispense(
    payload: TouchStoreImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import a dispense event from TouchStore Rx.
    Triggers FEFO deduction logic per Requirement 2.
    """
    # Validate medicine exists
    med = db.query(Medicine).filter(Medicine.id == payload.product_id).first()
    if not med:
        raise HTTPException(
            status_code=422,
            detail=f"Unrecognised product_id {payload.product_id} — medicine not found in system",
        )

    try:
        txn = FEFOService.apply_dispense(
            medicine_id=payload.product_id,
            quantity=payload.quantity,
            db=db,
            served_by_user_id=current_user.id,
            source=DispenseSource.TOUCHSTORE_RX,
            touchstore_ref=payload.touchstore_ref,
            prescription_ref=payload.prescription_ref,
        )
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient stock: requested {e.requested}, available {e.available}",
        )

    data = DispenseTransactionRead.model_validate(txn)
    data.medicine_name = med.name
    return data


@router.get("/reconciliation-flags", response_model=List[ReconciliationFlag])
def reconciliation_flags(
    touchstore_quantities: Optional[str] = Query(
        None,
        description="Comma-separated medicine_id:quantity pairs, e.g. '1:50,2:30'",
    ),
    db: Session = Depends(get_db),
):
    """
    Compare TouchStore Rx reported quantities against system on-hand.
    Flags products that differ by more than the configured tolerance.
    """
    if not touchstore_quantities:
        return []

    flags = []
    tolerance = settings.TOUCHSTORE_QTY_TOLERANCE

    pairs = touchstore_quantities.split(",")
    for pair in pairs:
        parts = pair.strip().split(":")
        if len(parts) != 2:
            continue
        try:
            med_id = int(parts[0])
            ts_qty = int(parts[1])
        except ValueError:
            continue

        med = db.query(Medicine).filter(Medicine.id == med_id).first()
        if not med:
            continue

        system_qty = FEFOService.get_on_hand(med_id, db)
        discrepancy = abs(system_qty - ts_qty)

        if discrepancy > tolerance:
            flags.append(ReconciliationFlag(
                medicine_id=med_id,
                medicine_name=med.name,
                system_on_hand=system_qty,
                touchstore_reported=ts_qty,
                discrepancy=discrepancy,
            ))

    return flags


@router.post("/reconcile/{medicine_id}", response_model=ReconciliationRead, status_code=201)
def reconcile(
    medicine_id: int,
    payload: ReconciliationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a manual reconciliation adjustment.
    Records the before/after on-hand quantities and the user's reason.
    """
    med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")

    qty_before = FEFOService.get_on_hand(medicine_id, db)

    # For now, the reconciliation is an audit record only — actual pack adjustments
    # would require a separate stock-take workflow. The after quantity equals
    # the touchstore-reported value if provided, else the current system value.
    qty_after = payload.touchstore_reported if payload.touchstore_reported is not None else qty_before

    adj = ReconciliationAdjustment(
        medicine_id=medicine_id,
        quantity_before=qty_before,
        quantity_after=qty_after,
        reason=payload.reason,
        adjusted_by_user_id=current_user.id,
        touchstore_reported=payload.touchstore_reported,
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)

    return ReconciliationRead.model_validate(adj)
