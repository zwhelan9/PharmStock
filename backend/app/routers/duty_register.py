"""
Duty Register Router
=====================
Records pharmacists on duty each day. Append-only with corrections.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.cd_register import DutyRegisterEntry
from app.schemas.cd_register import (
    DutyRegisterEntryCreate,
    DutyRegisterCorrectionCreate,
    DutyRegisterEntryRead,
)
from app.services.cd_register import DutyRegisterService

router = APIRouter(prefix="/duty-register", tags=["Duty Register"])


def _enrich(entry: DutyRegisterEntry) -> DutyRegisterEntryRead:
    data = DutyRegisterEntryRead.model_validate(entry)
    if entry.pharmacist:
        data.pharmacist_name = entry.pharmacist.full_name or entry.pharmacist.username
    if entry.entered_by:
        data.entered_by_username = entry.entered_by.username
    return data


@router.post("/", response_model=DutyRegisterEntryRead, status_code=201)
def create_duty_entry(
    payload: DutyRegisterEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = DutyRegisterService.create_entry(
        duty_date=payload.duty_date,
        pharmacist_user_id=payload.pharmacist_user_id,
        role=payload.role,
        entered_by_user_id=current_user.id,
        db=db,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return _enrich(entry)


@router.get("/", response_model=List[DutyRegisterEntryRead])
def list_duty_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_voided: bool = Query(False),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(DutyRegisterEntry)
    if not include_voided:
        q = q.filter(DutyRegisterEntry.is_voided == False)
    if start_date:
        q = q.filter(DutyRegisterEntry.duty_date >= start_date)
    if end_date:
        q = q.filter(DutyRegisterEntry.duty_date <= end_date)
    entries = q.order_by(DutyRegisterEntry.duty_date.desc(), DutyRegisterEntry.created_at.desc()).limit(limit).all()
    return [_enrich(e) for e in entries]


@router.post("/{entry_id}/correct", response_model=DutyRegisterEntryRead, status_code=201)
def correct_duty_entry(
    entry_id: int,
    payload: DutyRegisterCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    correction = DutyRegisterService.correct_entry(
        original_id=entry_id,
        correction_reason=payload.correction_reason,
        entered_by_user_id=current_user.id,
        db=db,
        duty_date=payload.duty_date,
        pharmacist_user_id=payload.pharmacist_user_id,
        role=payload.role,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return _enrich(correction)
