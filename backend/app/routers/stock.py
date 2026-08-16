from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.stock_log import StockLog

router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/levels")
def stock_levels(
    low_stock_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Current stock level for every medicine."""
    medicines = db.query(Medicine).order_by(Medicine.name).all()
    result = []
    for m in medicines:
        total = (
            db.query(func.sum(Batch.quantity_remaining))
            .filter(Batch.medicine_id == m.id, Batch.is_active == True)
            .scalar() or 0
        )
        is_low = total <= m.reorder_level
        if low_stock_only and not is_low:
            continue
        result.append({
            "medicine_id": m.id,
            "medicine_name": m.name,
            "category": m.category,
            "unit": m.unit,
            "total_stock": total,
            "reorder_level": m.reorder_level,
            "reorder_quantity": m.reorder_quantity,
            "is_low_stock": is_low,
        })
    return result


@router.get("/logs")
def stock_logs(
    medicine_id: Optional[int] = Query(None),
    change_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(StockLog)
    if medicine_id:
        query = query.filter(StockLog.medicine_id == medicine_id)
    if change_type:
        query = query.filter(StockLog.change_type == change_type)

    logs = query.order_by(StockLog.log_date.desc()).offset(offset).limit(limit).all()

    result = []
    for log in logs:
        med = db.query(Medicine.name).filter(Medicine.id == log.medicine_id).first()
        # Normalise change_type — SQLite may return raw string
        ct = log.change_type
        if hasattr(ct, 'value'):
            ct = ct.value
        result.append({
            "id": log.id,
            "medicine_id": log.medicine_id,
            "batch_id": log.batch_id,
            "change_type": ct,
            "quantity": log.quantity,
            "stock_before": log.stock_before,
            "stock_after": log.stock_after,
            "reference": log.reference,
            "performed_by": log.performed_by,
            "notes": log.notes,
            "log_date": log.log_date.isoformat() if log.log_date else None,
            "medicine_name": med[0] if med else None,
        })
    return result


@router.get("/summary")
def stock_summary(db: Session = Depends(get_db)):
    """Aggregate KPIs for the dashboard."""
    today = date.today()

    total_medicines = db.query(func.count(Medicine.id)).scalar() or 0

    # Low stock count
    medicines = db.query(Medicine).all()
    low_stock_count = 0
    for m in medicines:
        total = (
            db.query(func.sum(Batch.quantity_remaining))
            .filter(Batch.medicine_id == m.id, Batch.is_active == True)
            .scalar() or 0
        )
        if total <= m.reorder_level:
            low_stock_count += 1

    # Expiry counts
    from app.core.config import settings
    from datetime import timedelta

    critical_date = today + timedelta(days=settings.EXPIRY_CRITICAL_DAYS)
    warning_date = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)
    watch_date = today + timedelta(days=settings.EXPIRY_WATCH_DAYS)

    expiring_critical = (
        db.query(func.count(Batch.id))
        .filter(
            Batch.is_active == True,
            Batch.expiry_date >= today,
            Batch.expiry_date <= critical_date,
        )
        .scalar() or 0
    )
    expiring_warning = (
        db.query(func.count(Batch.id))
        .filter(
            Batch.is_active == True,
            Batch.expiry_date > critical_date,
            Batch.expiry_date <= warning_date,
        )
        .scalar() or 0
    )
    expiring_watch = (
        db.query(func.count(Batch.id))
        .filter(
            Batch.is_active == True,
            Batch.expiry_date > warning_date,
            Batch.expiry_date <= watch_date,
        )
        .scalar() or 0
    )
    expired_active = (
        db.query(func.count(Batch.id))
        .filter(Batch.is_active == True, Batch.expiry_date < today)
        .scalar() or 0
    )

    # Total stock value
    from app.models.medicine import Medicine as Med
    batches = db.query(Batch).filter(Batch.is_active == True).all()
    total_value = sum(
        (b.cost_price or 0) * b.quantity_remaining for b in batches
    )

    return {
        "total_medicines": total_medicines,
        "low_stock_count": low_stock_count,
        "expired_active_batches": expired_active,
        "expiring_critical": expiring_critical,
        "expiring_warning": expiring_warning,
        "expiring_watch": expiring_watch,
        "total_stock_value": round(total_value, 2),
    }
