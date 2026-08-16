from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.expiry_log import ExpiryLog
from app.schemas.expiry_log import ExpiryLogCreate, ExpiryLogRead
from app.core.config import settings

router = APIRouter(prefix="/expiry", tags=["Expiry"])


def _expiry_log_to_read(e: ExpiryLog, db: Session) -> ExpiryLogRead:
    med = db.query(Medicine.name).filter(Medicine.id == e.medicine_id).first()
    batch = db.query(Batch.batch_number).filter(Batch.id == e.batch_id).first()
    return ExpiryLogRead(
        id=e.id,
        medicine_id=e.medicine_id,
        batch_id=e.batch_id,
        expiry_date=e.expiry_date,
        quantity_affected=e.quantity_affected,
        quantity_wasted=e.quantity_wasted,
        estimated_loss=e.estimated_loss,
        action=e.action,
        action_date=e.action_date,
        performed_by=e.performed_by,
        notes=e.notes,
        created_at=e.created_at,
        medicine_name=med[0] if med else None,
        batch_number=batch[0] if batch else None,
    )


@router.get("/alerts")
def expiry_alerts(db: Session = Depends(get_db)):
    """
    Returns batches grouped into expiry alert tiers:
    expired, critical (≤30d), warning (≤60d), watch (≤90d).
    """
    today = date.today()
    critical_date = today + timedelta(days=settings.EXPIRY_CRITICAL_DAYS)
    warning_date = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)
    watch_date = today + timedelta(days=settings.EXPIRY_WATCH_DAYS)

    batches = (
        db.query(Batch)
        .filter(Batch.is_active == True, Batch.expiry_date <= watch_date)
        .order_by(Batch.expiry_date.asc())
        .all()
    )

    def serialize(b: Batch, tier: str):
        med = db.query(Medicine).filter(Medicine.id == b.medicine_id).first()
        days_left = (b.expiry_date - today).days
        return {
            "batch_id": b.id,
            "batch_number": b.batch_number,
            "medicine_id": b.medicine_id,
            "medicine_name": med.name if med else "Unknown",
            "category": med.category if med else None,
            "expiry_date": b.expiry_date.isoformat(),
            "days_until_expiry": days_left,
            "quantity_remaining": b.quantity_remaining,
            "cost_price": b.cost_price,
            "estimated_loss": round((b.cost_price or 0) * b.quantity_remaining, 2),
            "tier": tier,
        }

    expired = [serialize(b, "expired") for b in batches if b.expiry_date < today]
    critical = [serialize(b, "critical") for b in batches if today <= b.expiry_date <= critical_date]
    warning = [serialize(b, "warning") for b in batches if critical_date < b.expiry_date <= warning_date]
    watch = [serialize(b, "watch") for b in batches if warning_date < b.expiry_date <= watch_date]

    return {
        "expired": expired,
        "critical": critical,
        "warning": warning,
        "watch": watch,
        "summary": {
            "expired_count": len(expired),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "watch_count": len(watch),
            "total_estimated_loss": round(
                sum(b["estimated_loss"] for b in expired + critical), 2
            ),
        },
    }


@router.get("/logs", response_model=List[ExpiryLogRead])
def list_expiry_logs(
    medicine_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(ExpiryLog)
    if medicine_id:
        query = query.filter(ExpiryLog.medicine_id == medicine_id)
    logs = query.order_by(ExpiryLog.action_date.desc()).offset(offset).limit(limit).all()
    return [_expiry_log_to_read(e, db) for e in logs]


@router.post("/logs", response_model=ExpiryLogRead, status_code=201)
def create_expiry_log(payload: ExpiryLogCreate, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Compute estimated loss if not provided
    estimated_loss = payload.estimated_loss
    if estimated_loss is None and batch.cost_price:
        wasted = payload.quantity_wasted or payload.quantity_affected
        estimated_loss = round(batch.cost_price * wasted, 2)

    log = ExpiryLog(
        medicine_id=payload.medicine_id,
        batch_id=payload.batch_id,
        expiry_date=payload.expiry_date,
        quantity_affected=payload.quantity_affected,
        quantity_wasted=payload.quantity_wasted,
        estimated_loss=estimated_loss,
        action=payload.action,
        action_date=payload.action_date,
        performed_by=payload.performed_by,
        notes=payload.notes,
    )
    db.add(log)

    # Mark batch inactive
    batch.is_active = False
    db.commit()
    db.refresh(log)
    return _expiry_log_to_read(log, db)


@router.get("/calendar")
def expiry_calendar(
    months_ahead: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Returns batches expiring within the next N months, grouped by month."""
    today = date.today()
    end_date = today + timedelta(days=months_ahead * 30)

    batches = (
        db.query(Batch)
        .filter(
            Batch.is_active == True,
            Batch.expiry_date >= today,
            Batch.expiry_date <= end_date,
        )
        .order_by(Batch.expiry_date.asc())
        .all()
    )

    grouped: dict = {}
    for b in batches:
        key = b.expiry_date.strftime("%Y-%m")
        med = db.query(Medicine).filter(Medicine.id == b.medicine_id).first()
        entry = {
            "batch_id": b.id,
            "batch_number": b.batch_number,
            "medicine_id": b.medicine_id,
            "medicine_name": med.name if med else "Unknown",
            "expiry_date": b.expiry_date.isoformat(),
            "quantity_remaining": b.quantity_remaining,
            "days_until_expiry": (b.expiry_date - today).days,
        }
        grouped.setdefault(key, []).append(entry)

    return grouped
