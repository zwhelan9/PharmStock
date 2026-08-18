"""
Dispense Router
===============
FEFO-based dispensing endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.medicine import Medicine
from app.models.dispense_transaction import DispenseTransaction, DispenseSource
from app.schemas.dispense import DispenseRequest, DispenseTransactionRead
from app.services.fefo import FEFOService, InsufficientStockError

router = APIRouter(prefix="/dispense", tags=["Dispense"])


@router.post("/", response_model=DispenseTransactionRead, status_code=201)
def dispense(
    payload: DispenseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a manual dispense — automatically selects packs via FEFO."""
    # Validate medicine exists
    med = db.query(Medicine).filter(Medicine.id == payload.medicine_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")

    try:
        txn = FEFOService.apply_dispense(
            medicine_id=payload.medicine_id,
            quantity=payload.quantity,
            db=db,
            served_by_user_id=current_user.id,
            source=DispenseSource.MANUAL,
            prescription_ref=payload.prescription_ref,
            notes=payload.notes,
        )
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient stock: requested {e.requested}, available {e.available}",
        )

    # Build response with line items
    data = DispenseTransactionRead.model_validate(txn)
    data.medicine_name = med.name
    return data


@router.get("/", response_model=List[DispenseTransactionRead])
def list_dispenses(
    medicine_id: int = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(DispenseTransaction)
    if medicine_id:
        q = q.filter(DispenseTransaction.medicine_id == medicine_id)
    txns = q.order_by(DispenseTransaction.dispense_date.desc()).limit(limit).all()

    result = []
    for txn in txns:
        data = DispenseTransactionRead.model_validate(txn)
        data.medicine_name = txn.medicine.name if txn.medicine else None
        result.append(data)
    return result


@router.get("/{txn_id}", response_model=DispenseTransactionRead)
def get_dispense(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(DispenseTransaction).filter(DispenseTransaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Dispense transaction not found")
    data = DispenseTransactionRead.model_validate(txn)
    data.medicine_name = txn.medicine.name if txn.medicine else None
    return data
