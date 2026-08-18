"""
CD Destruction Router
======================
Destruction records with witness re-authentication and digital signature.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.cd_register import CDDestructionRecord
from app.schemas.cd_register import CDDestructionCreate, CDDestructionRead
from app.services.cd_register import CDDestructionService

router = APIRouter(prefix="/cd-destruction", tags=["CD Destruction"])


def _enrich(record: CDDestructionRecord) -> CDDestructionRead:
    data = CDDestructionRead.model_validate(record)
    if record.witnessed_by:
        data.witness_name = record.witnessed_by.full_name or record.witnessed_by.username
    if record.created_by:
        data.created_by_username = record.created_by.username
    return data


@router.post("/", response_model=CDDestructionRead, status_code=201)
def create_destruction(
    payload: CDDestructionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a CD destruction event.
    Requires witness re-authentication (password) per FR-CD-1.4 and FR-CD-5.2.
    """
    record = CDDestructionService.create_record(
        date_of_destruction=payload.date_of_destruction,
        medicine_id=payload.medicine_id,
        quantity_destroyed=payload.quantity_destroyed,
        witnessed_by_user_id=payload.witnessed_by_user_id,
        witness_password=payload.witness_password,
        linked_register_entry_ids=payload.linked_register_entry_ids,
        created_by_user_id=current_user.id,
        db=db,
    )
    return _enrich(record)


@router.get("/", response_model=List[CDDestructionRead])
def list_destructions(
    medicine_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(CDDestructionRecord)
    if medicine_id:
        q = q.filter(CDDestructionRecord.medicine_id == medicine_id)
    records = q.order_by(CDDestructionRecord.date_of_destruction.desc()).limit(limit).all()
    return [_enrich(r) for r in records]


@router.get("/{record_id}", response_model=CDDestructionRead)
def get_destruction(record_id: int, db: Session = Depends(get_db)):
    record = db.query(CDDestructionRecord).filter(CDDestructionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Destruction record not found")
    return _enrich(record)
