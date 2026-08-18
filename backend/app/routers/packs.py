"""
Pack Instances Router
=====================
CRUD for physical pack tracking + on-hand + expiry alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.models.pack_instance import PackInstance, PackStatus
from app.models.medicine import Medicine
from app.schemas.pack_instance import (
    PackInstanceCreate,
    PackInstanceRead,
    PackInstanceUpdate,
    OnHandResponse,
)
from app.services.fefo import FEFOService

router = APIRouter(prefix="/packs", tags=["Pack Instances"])


@router.get("/", response_model=List[PackInstanceRead])
def list_packs(
    medicine_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(PackInstance)
    if medicine_id:
        q = q.filter(PackInstance.medicine_id == medicine_id)
    if status:
        q = q.filter(PackInstance.status == status)
    packs = q.order_by(PackInstance.expiry_date.asc()).all()
    result = []
    for p in packs:
        data = PackInstanceRead.model_validate(p)
        data.medicine_name = p.medicine.name if p.medicine else None
        result.append(data)
    return result


@router.get("/expiry-alerts", response_model=List[PackInstanceRead])
def expiry_alerts(db: Session = Depends(get_db)):
    """Packs within the alert window, sorted: open before sealed, earliest expiry first."""
    today = date.today()
    alert_cutoff = today + timedelta(days=settings.PACK_EXPIRY_ALERT_DAYS)

    packs = (
        db.query(PackInstance)
        .filter(
            PackInstance.status.in_([PackStatus.SEALED, PackStatus.OPEN]),
            PackInstance.quantity_remaining > 0,
            PackInstance.expiry_date <= alert_cutoff,
        )
        .order_by(
            # open packs first (0 for open, 1 for sealed)
            (PackInstance.status == PackStatus.SEALED).asc(),
            PackInstance.expiry_date.asc(),
        )
        .all()
    )
    result = []
    for p in packs:
        data = PackInstanceRead.model_validate(p)
        data.medicine_name = p.medicine.name if p.medicine else None
        result.append(data)
    return result


@router.get("/medicine/{medicine_id}/on-hand", response_model=OnHandResponse)
def on_hand(medicine_id: int, db: Session = Depends(get_db)):
    qty = FEFOService.get_on_hand(medicine_id, db)
    return OnHandResponse(medicine_id=medicine_id, on_hand_quantity=qty)


@router.get("/{pack_id}", response_model=PackInstanceRead)
def get_pack(pack_id: int, db: Session = Depends(get_db)):
    p = db.query(PackInstance).filter(PackInstance.id == pack_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pack instance not found")
    data = PackInstanceRead.model_validate(p)
    data.medicine_name = p.medicine.name if p.medicine else None
    return data


@router.post("/", response_model=PackInstanceRead, status_code=201)
def create_pack(payload: PackInstanceCreate, db: Session = Depends(get_db)):
    """Create a new pack instance (delivery receipt)."""
    # Validate medicine exists
    med = db.query(Medicine).filter(Medicine.id == payload.medicine_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # Validate required fields
    if not payload.batch_number:
        raise HTTPException(status_code=422, detail="batch_number is required")

    pack = PackInstance(
        medicine_id=payload.medicine_id,
        batch_id=payload.batch_id,
        batch_number=payload.batch_number,
        lot_number=payload.lot_number,
        expiry_date=payload.expiry_date,
        quantity_received=payload.quantity_received,
        quantity_remaining=payload.quantity_received,
        unit_cost=payload.unit_cost,
        status=PackStatus.SEALED,
        is_controlled_drug=payload.is_controlled_drug,
        supplier_invoice=payload.supplier_invoice,
        notes=payload.notes,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)

    data = PackInstanceRead.model_validate(pack)
    data.medicine_name = med.name
    return data


@router.patch("/{pack_id}", response_model=PackInstanceRead)
def update_pack(pack_id: int, payload: PackInstanceUpdate, db: Session = Depends(get_db)):
    pack = db.query(PackInstance).filter(PackInstance.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack instance not found")

    if payload.notes is not None:
        pack.notes = payload.notes
    if payload.is_controlled_drug is not None:
        pack.is_controlled_drug = payload.is_controlled_drug

    db.commit()
    db.refresh(pack)
    data = PackInstanceRead.model_validate(pack)
    data.medicine_name = pack.medicine.name if pack.medicine else None
    return data
