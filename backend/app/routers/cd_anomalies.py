"""
CD Anomaly Detection (FR-CD-7.5)
=================================
Flags unusual patterns for pharmacist review:
- Spikes in a single CD's dispensing
- Repeated corrections on the same entry
- Unusually high supply-to-prescription ratio
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.models.cd_register import CDRegisterEntry, CDTransactionType
from app.models.medicine import Medicine

router = APIRouter(prefix="/cd-anomalies", tags=["CD Anomalies"])


@router.get("/")
def cd_anomalies(
    lookback_days: int = Query(30, description="Analysis window in days"),
    db: Session = Depends(get_db),
):
    """
    FR-CD-7.5: Flag unusual CD patterns for pharmacist review.
    """
    cutoff = datetime.now() - timedelta(days=lookback_days)
    anomalies = []

    # Get all CD medicines with recent activity
    recent_entries = (
        db.query(CDRegisterEntry)
        .filter(CDRegisterEntry.created_at >= cutoff, CDRegisterEntry.is_voided == False)
        .all()
    )

    # Group by medicine
    by_medicine = {}
    for e in recent_entries:
        if e.medicine_id not in by_medicine:
            by_medicine[e.medicine_id] = {"receipts": [], "supplies": [], "corrections": []}
        if e.is_correction:
            by_medicine[e.medicine_id]["corrections"].append(e)
        elif e.transaction_type == CDTransactionType.RECEIPT:
            by_medicine[e.medicine_id]["receipts"].append(e)
        else:
            by_medicine[e.medicine_id]["supplies"].append(e)

    for med_id, data in by_medicine.items():
        med = db.query(Medicine).filter(Medicine.id == med_id).first()
        med_name = med.name if med else f"Medicine #{med_id}"

        # 1. Spike detection: compare recent 7d vs rest of lookback
        recent_7d_cutoff = datetime.now() - timedelta(days=7)
        recent_supply_qty = sum(
            e.quantity for e in data["supplies"]
            if e.created_at and e.created_at >= recent_7d_cutoff
        )
        older_supply_qty = sum(
            e.quantity for e in data["supplies"]
            if e.created_at and e.created_at < recent_7d_cutoff
        )
        older_days = max(lookback_days - 7, 1)
        avg_daily_older = older_supply_qty / older_days
        avg_daily_recent = recent_supply_qty / 7.0

        if avg_daily_older > 0.5 and avg_daily_recent > avg_daily_older * 2:
            anomalies.append({
                "type": "dispensing_spike",
                "severity": "high",
                "medicine_id": med_id,
                "medicine_name": med_name,
                "detail": f"Recent 7-day dispensing ({recent_supply_qty} units, avg {avg_daily_recent:.1f}/day) is {avg_daily_recent/avg_daily_older:.1f}x the prior average ({avg_daily_older:.1f}/day)",
            })

        # 2. Repeated corrections
        correction_count = len(data["corrections"])
        if correction_count >= 3:
            anomalies.append({
                "type": "repeated_corrections",
                "severity": "medium",
                "medicine_id": med_id,
                "medicine_name": med_name,
                "detail": f"{correction_count} corrections in the last {lookback_days} days — review for pattern",
            })

        # 3. Supply-to-receipt ratio (high supply with low receipts could indicate leakage)
        total_supply = sum(e.quantity for e in data["supplies"])
        total_receipt = sum(e.quantity for e in data["receipts"])
        if total_receipt > 0 and total_supply > total_receipt * 1.5:
            anomalies.append({
                "type": "high_supply_ratio",
                "severity": "medium",
                "medicine_id": med_id,
                "medicine_name": med_name,
                "detail": f"Supply ({total_supply} units) significantly exceeds receipts ({total_receipt} units) in the period — verify balance reconciliation",
            })

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: severity_order.get(a["severity"], 9))

    return {
        "lookback_days": lookback_days,
        "total_anomalies": len(anomalies),
        "high_count": sum(1 for a in anomalies if a["severity"] == "high"),
        "anomalies": anomalies,
    }
