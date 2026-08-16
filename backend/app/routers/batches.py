from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.stock_log import StockLog, ChangeType
from app.schemas.batch import BatchCreate, BatchUpdate, BatchRead
from app.core.config import settings

router = APIRouter(prefix="/batches", tags=["Batches"])


def _expiry_status(expiry_date: date):
    today = date.today()
    days = (expiry_date - today).days
    if days < 0:
        status = "expired"
    elif days <= settings.EXPIRY_CRITICAL_DAYS:
        status = "critical"
    elif days <= settings.EXPIRY_WARNING_DAYS:
        status = "warning"
    elif days <= settings.EXPIRY_WATCH_DAYS:
        status = "watch"
    else:
        status = "ok"
    return status, days


def _batch_to_read(b: Batch) -> BatchRead:
    status, days = _expiry_status(b.expiry_date)
    return BatchRead(
        id=b.id,
        medicine_id=b.medicine_id,
        batch_number=b.batch_number,
        supplier_invoice=b.supplier_invoice,
        supplier=b.supplier,
        quantity_received=b.quantity_received,
        quantity_remaining=b.quantity_remaining,
        cost_price=b.cost_price,
        purchase_date=b.purchase_date,
        manufacture_date=b.manufacture_date,
        expiry_date=b.expiry_date,
        is_active=b.is_active,
        is_quarantined=b.is_quarantined,
        notes=b.notes,
        created_at=b.created_at,
        days_until_expiry=days,
        expiry_status=status,
    )


# ── Static / prefix routes BEFORE /{batch_id} ────────────────────────────────

@router.get("/medicine/{medicine_id}/fefo", response_model=List[BatchRead])
def fefo_order(medicine_id: int, db: Session = Depends(get_db)):
    """Return active batches in FEFO order (First Expired First Out)."""
    batches = (
        db.query(Batch)
        .filter(
            Batch.medicine_id == medicine_id,
            Batch.is_active == True,
            Batch.is_quarantined == False,
            Batch.expiry_date >= date.today(),
        )
        .order_by(Batch.expiry_date.asc())
        .all()
    )
    return [_batch_to_read(b) for b in batches]


@router.get("/", response_model=List[BatchRead])
def list_batches(
    medicine_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    expiry_status: Optional[str] = Query(None, description="expired|critical|warning|watch|ok"),
    db: Session = Depends(get_db),
):
    query = db.query(Batch)
    if medicine_id:
        query = query.filter(Batch.medicine_id == medicine_id)
    if active_only:
        query = query.filter(Batch.is_active == True)

    batches = query.order_by(Batch.expiry_date.asc()).all()
    result = [_batch_to_read(b) for b in batches]

    if expiry_status:
        result = [b for b in result if b.expiry_status == expiry_status]

    return result


# ── Parameterised routes AFTER static ones ───────────────────────────────────

@router.get("/{batch_id}", response_model=BatchRead)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.id == batch_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_read(b)


@router.post("/", response_model=BatchRead, status_code=201)
def create_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    medicine = db.query(Medicine).filter(Medicine.id == payload.medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    if payload.expiry_date <= date.today():
        raise HTTPException(status_code=400, detail="Expiry date must be in the future")

    data = payload.model_dump()
    if data.get("quantity_remaining") is None:
        data["quantity_remaining"] = data["quantity_received"]

    b = Batch(**data)
    db.add(b)
    db.flush()

    total_before = (
        db.query(Batch)
        .filter(Batch.medicine_id == b.medicine_id, Batch.is_active == True, Batch.id != b.id)
        .with_entities(Batch.quantity_remaining)
        .all()
    )
    stock_before = sum(r[0] for r in total_before)
    log = StockLog(
        medicine_id=b.medicine_id,
        batch_id=b.id,
        change_type=ChangeType.STOCK_IN,
        quantity=b.quantity_received,
        stock_before=stock_before,
        stock_after=stock_before + b.quantity_received,
        reference=b.supplier_invoice,
        notes=f"Batch {b.batch_number} received",
    )
    db.add(log)
    db.commit()
    db.refresh(b)
    return _batch_to_read(b)


@router.patch("/{batch_id}", response_model=BatchRead)
def update_batch(batch_id: int, payload: BatchUpdate, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.id == batch_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Batch not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(b, field, value)
    db.commit()
    db.refresh(b)
    return _batch_to_read(b)
