from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta

from app.core.database import get_db
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.core.config import settings

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/")
def get_all_alerts(db: Session = Depends(get_db)):
    """
    Returns a consolidated list of all active alerts across categories:
    - low_stock
    - expiring_critical
    - expiring_warning
    - expired_in_stock
    - reorder_suggested
    """
    today = date.today()
    critical_date = today + timedelta(days=settings.EXPIRY_CRITICAL_DAYS)
    warning_date = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    alerts = []

    # ── Expiry alerts ──────────────────────────────────────────────────────
    batches = (
        db.query(Batch)
        .filter(Batch.is_active == True, Batch.expiry_date <= warning_date)
        .order_by(Batch.expiry_date.asc())
        .all()
    )

    for b in batches:
        med = db.query(Medicine).filter(Medicine.id == b.medicine_id).first()
        days_left = (b.expiry_date - today).days
        if days_left < 0:
            severity = "high"
            alert_type = "expired_in_stock"
            message = (
                f"EXPIRED: {med.name if med else 'Unknown'} batch {b.batch_number} "
                f"expired {abs(days_left)} day(s) ago — {b.quantity_remaining} units still active"
            )
        elif days_left <= settings.EXPIRY_CRITICAL_DAYS:
            severity = "high"
            alert_type = "expiring_critical"
            message = (
                f"CRITICAL: {med.name if med else 'Unknown'} batch {b.batch_number} "
                f"expires in {days_left} day(s) — {b.quantity_remaining} units remaining"
            )
        else:
            severity = "medium"
            alert_type = "expiring_warning"
            message = (
                f"WARNING: {med.name if med else 'Unknown'} batch {b.batch_number} "
                f"expires in {days_left} day(s) — {b.quantity_remaining} units remaining"
            )

        alerts.append({
            "type": alert_type,
            "severity": severity,
            "medicine_id": b.medicine_id,
            "medicine_name": med.name if med else "Unknown",
            "batch_id": b.id,
            "batch_number": b.batch_number,
            "expiry_date": b.expiry_date.isoformat(),
            "days_until_expiry": days_left,
            "quantity_affected": b.quantity_remaining,
            "message": message,
        })

    # ── Low stock alerts ───────────────────────────────────────────────────
    medicines = db.query(Medicine).all()
    for m in medicines:
        total = (
            db.query(func.sum(Batch.quantity_remaining))
            .filter(Batch.medicine_id == m.id, Batch.is_active == True)
            .scalar() or 0
        )
        if total <= m.reorder_level:
            severity = "high" if total == 0 else "medium"
            alerts.append({
                "type": "low_stock",
                "severity": severity,
                "medicine_id": m.id,
                "medicine_name": m.name,
                "batch_id": None,
                "batch_number": None,
                "quantity_affected": total,
                "reorder_quantity": m.reorder_quantity,
                "message": (
                    f"{'OUT OF STOCK' if total == 0 else 'LOW STOCK'}: {m.name} — "
                    f"{total} units remaining (reorder level: {m.reorder_level}). "
                    f"Suggested order: {m.reorder_quantity} units."
                ),
            })

    # Sort: high severity first, then by type
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

    return {
        "total": len(alerts),
        "high_count": sum(1 for a in alerts if a["severity"] == "high"),
        "medium_count": sum(1 for a in alerts if a["severity"] == "medium"),
        "alerts": alerts,
    }
