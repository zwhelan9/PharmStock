"""
CD Register Router
===================
Controlled Drugs Register CRUD, corrections, export.
Append-only with full audit trail.
"""

import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.cd_register import CDRegisterEntry
from app.schemas.cd_register import (
    CDRegisterEntryCreate,
    CDRegisterCorrectionCreate,
    CDRegisterEntryRead,
)
from app.services.cd_register import CDRegisterService

router = APIRouter(prefix="/cd-register", tags=["CD Register"])


def _enrich(entry: CDRegisterEntry) -> CDRegisterEntryRead:
    data = CDRegisterEntryRead.model_validate(entry)
    if entry.entered_by:
        data.entered_by_username = entry.entered_by.username
    return data


@router.post("/entries", response_model=CDRegisterEntryRead, status_code=201)
def create_entry(
    payload: CDRegisterEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new CD register entry (receipt or supply)."""
    entry = CDRegisterService.create_entry(
        transaction_type=payload.transaction_type,
        transaction_date=payload.transaction_date,
        medicine_id=payload.medicine_id,
        quantity=payload.quantity,
        counterparty_name=payload.counterparty_name,
        counterparty_address=payload.counterparty_address,
        authority_reference=payload.authority_reference,
        prescriber_name=payload.prescriber_name,
        prescriber_reg_number=payload.prescriber_reg_number,
        user_id=current_user.id,
        db=db,
    )
    return _enrich(entry)


@router.get("/entries", response_model=List[CDRegisterEntryRead])
def list_entries(
    medicine_id: Optional[int] = None,
    include_voided: bool = Query(False),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    """List CD register entries, optionally filtered by medicine."""
    q = db.query(CDRegisterEntry)
    if medicine_id:
        q = q.filter(CDRegisterEntry.medicine_id == medicine_id)
    if not include_voided:
        q = q.filter(CDRegisterEntry.is_voided == False)
    entries = q.order_by(CDRegisterEntry.created_at.desc()).limit(limit).all()
    return [_enrich(e) for e in entries]


@router.get("/entries/{entry_id}", response_model=CDRegisterEntryRead)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(CDRegisterEntry).filter(CDRegisterEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _enrich(entry)


@router.get("/entries/{entry_id}/history", response_model=List[CDRegisterEntryRead])
def get_entry_history(entry_id: int, db: Session = Depends(get_db)):
    """Get correction history for a specific entry."""
    # Get all entries in the correction chain
    entries = []
    # Original
    original = db.query(CDRegisterEntry).filter(CDRegisterEntry.id == entry_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Entry not found")
    entries.append(original)
    # Corrections referencing this entry
    corrections = (
        db.query(CDRegisterEntry)
        .filter(CDRegisterEntry.correction_of_entry_id == entry_id)
        .order_by(CDRegisterEntry.created_at.asc())
        .all()
    )
    entries.extend(corrections)
    return [_enrich(e) for e in entries]


@router.post("/entries/{entry_id}/correct", response_model=CDRegisterEntryRead, status_code=201)
def correct_entry(
    entry_id: int,
    payload: CDRegisterCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a correction for an existing entry (append-only — original is voided, not deleted)."""
    correction = CDRegisterService.correct_entry(
        original_entry_id=entry_id,
        correction_reason=payload.correction_reason,
        user_id=current_user.id,
        db=db,
        transaction_type=payload.transaction_type,
        transaction_date=payload.transaction_date,
        quantity=payload.quantity,
        counterparty_name=payload.counterparty_name,
        counterparty_address=payload.counterparty_address,
        authority_reference=payload.authority_reference,
        prescriber_name=payload.prescriber_name,
        prescriber_reg_number=payload.prescriber_reg_number,
    )
    return _enrich(correction)


@router.get("/balance/{medicine_id}")
def get_balance(medicine_id: int, db: Session = Depends(get_db)):
    """Get current running balance for a CD product."""
    balance = CDRegisterService.get_running_balance(medicine_id, db)
    return {"medicine_id": medicine_id, "running_balance": balance}


@router.get("/export")
def export_register(
    medicine_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Export CD register as CSV (suitable for PSI inspection)."""
    q = db.query(CDRegisterEntry).filter(CDRegisterEntry.is_voided == False)
    if medicine_id:
        q = q.filter(CDRegisterEntry.medicine_id == medicine_id)
    if start_date:
        q = q.filter(CDRegisterEntry.transaction_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.filter(CDRegisterEntry.transaction_date <= datetime.combine(end_date, datetime.max.time()))

    entries = q.order_by(CDRegisterEntry.transaction_date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Type", "Product", "Strength", "Form", "Quantity",
        "Running Balance", "Counterparty", "Address", "Authority Ref",
        "Prescriber", "Prescriber Reg", "Entered By", "Correction",
    ])
    for e in entries:
        writer.writerow([
            e.transaction_date.isoformat() if e.transaction_date else "",
            e.transaction_type.value if hasattr(e.transaction_type, 'value') else e.transaction_type,
            e.product_name, e.product_strength or "", e.product_form or "",
            e.quantity, e.running_balance,
            e.counterparty_name, e.counterparty_address or "",
            e.authority_reference or "", e.prescriber_name or "",
            e.prescriber_reg_number or "",
            e.entered_by.username if e.entered_by else "",
            "Yes" if e.is_correction else "No",
        ])

    output.seek(0)
    filename = f"cd_register_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
