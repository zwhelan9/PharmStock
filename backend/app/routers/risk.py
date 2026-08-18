"""
Risk Detection Endpoints (FR-4.3, FR-4.4)
==========================================
- Slow-moving / dead stock detection
- Demand anomaly detection (spike/drop vs forecast)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime
from typing import Optional

from app.core.database import get_db
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.models.sale import Sale
from app.models.pack_instance import PackInstance, PackStatus

router = APIRouter(prefix="/risk", tags=["Risk Detection"])


@router.get("/dead-stock")
def dead_stock(
    days_threshold: int = Query(60, description="No sales in this many days = dead stock"),
    db: Session = Depends(get_db),
):
    """
    FR-4.3: Flag slow-moving / dead stock.
    Returns medicines with zero sales in the last N days that still have stock on hand.
    """
    today = date.today()
    cutoff = datetime.now() - timedelta(days=days_threshold)

    medicines = db.query(Medicine).order_by(Medicine.name).all()
    dead_items = []

    for med in medicines:
        # Check on-hand
        on_hand = (
            db.query(func.sum(Batch.quantity_remaining))
            .filter(Batch.medicine_id == med.id, Batch.is_active == True)
            .scalar() or 0
        )

        # Also check pack instances
        pack_on_hand = (
            db.query(func.sum(PackInstance.quantity_remaining))
            .filter(
                PackInstance.medicine_id == med.id,
                PackInstance.status.in_([PackStatus.SEALED, PackStatus.OPEN]),
                PackInstance.expiry_date >= today,
            )
            .scalar()
        )
        total_on_hand = pack_on_hand if pack_on_hand is not None else on_hand

        if total_on_hand <= 0:
            continue  # No stock = not dead stock, just out of stock

        # Check last sale date
        last_sale = (
            db.query(func.max(Sale.sale_date))
            .filter(Sale.medicine_id == med.id)
            .scalar()
        )

        # Count sales in threshold period
        recent_sales = (
            db.query(func.sum(Sale.quantity))
            .filter(Sale.medicine_id == med.id, Sale.sale_date >= cutoff)
            .scalar() or 0
        )

        if recent_sales == 0:
            days_since_last = (today - last_sale.date()).days if last_sale else 999

            # Estimate value at risk
            cost_per_unit = (
                db.query(Batch.cost_price)
                .filter(Batch.medicine_id == med.id, Batch.cost_price.isnot(None))
                .order_by(Batch.created_at.desc())
                .first()
            )
            unit_cost = cost_per_unit[0] if cost_per_unit else (med.selling_price * 0.5 if med.selling_price else 0)
            value_at_risk = round(total_on_hand * unit_cost, 2)

            dead_items.append({
                "medicine_id": med.id,
                "medicine_name": med.name,
                "category": med.category,
                "supplier": med.supplier,
                "on_hand_quantity": total_on_hand,
                "days_since_last_sale": days_since_last,
                "last_sale_date": last_sale.date().isoformat() if last_sale else None,
                "value_at_risk": value_at_risk,
            })

    # Sort by value at risk descending
    dead_items.sort(key=lambda x: x["value_at_risk"], reverse=True)

    return {
        "threshold_days": days_threshold,
        "total_dead_stock_items": len(dead_items),
        "total_value_at_risk": round(sum(d["value_at_risk"] for d in dead_items), 2),
        "items": dead_items,
    }


@router.get("/anomalies")
def demand_anomalies(
    lookback_days: int = Query(7, description="Compare last N days vs preceding period"),
    threshold_pct: float = Query(50.0, description="% deviation from average to flag as anomaly"),
    db: Session = Depends(get_db),
):
    """
    FR-4.4: Detect demand anomalies — sudden spikes or drops vs recent average.
    Compares the last `lookback_days` sales against the preceding 30-day average.
    Flags medicines where deviation exceeds `threshold_pct`.
    """
    today = datetime.now()
    recent_start = today - timedelta(days=lookback_days)
    baseline_start = today - timedelta(days=lookback_days + 30)
    baseline_end = recent_start

    medicines = db.query(Medicine).all()
    anomalies = []

    for med in medicines:
        # Recent period sales
        recent_qty = (
            db.query(func.sum(Sale.quantity))
            .filter(Sale.medicine_id == med.id, Sale.sale_date >= recent_start)
            .scalar() or 0
        )
        recent_daily = recent_qty / max(lookback_days, 1)

        # Baseline period sales (preceding 30 days)
        baseline_qty = (
            db.query(func.sum(Sale.quantity))
            .filter(
                Sale.medicine_id == med.id,
                Sale.sale_date >= baseline_start,
                Sale.sale_date < baseline_end,
            )
            .scalar() or 0
        )
        baseline_daily = baseline_qty / 30.0

        if baseline_daily < 1:
            # Skip very low volume items — not meaningful
            continue

        deviation_pct = ((recent_daily - baseline_daily) / baseline_daily) * 100

        if abs(deviation_pct) >= threshold_pct:
            anomaly_type = "spike" if deviation_pct > 0 else "drop"
            anomalies.append({
                "medicine_id": med.id,
                "medicine_name": med.name,
                "category": med.category,
                "anomaly_type": anomaly_type,
                "recent_daily_avg": round(recent_daily, 1),
                "baseline_daily_avg": round(baseline_daily, 1),
                "deviation_pct": round(deviation_pct, 1),
                "severity": "high" if abs(deviation_pct) >= 100 else "medium",
            })

    # Sort by absolute deviation descending
    anomalies.sort(key=lambda x: abs(x["deviation_pct"]), reverse=True)

    return {
        "lookback_days": lookback_days,
        "threshold_pct": threshold_pct,
        "total_anomalies": len(anomalies),
        "spikes": sum(1 for a in anomalies if a["anomaly_type"] == "spike"),
        "drops": sum(1 for a in anomalies if a["anomaly_type"] == "drop"),
        "anomalies": anomalies,
    }


@router.get("/stock-value")
def stock_value_breakdown(db: Session = Depends(get_db)):
    """
    FR-5.5: Stock value breakdown by category.
    """
    medicines = db.query(Medicine).all()
    categories = {}

    today = date.today()

    for med in medicines:
        batches = (
            db.query(Batch)
            .filter(Batch.medicine_id == med.id, Batch.is_active == True)
            .all()
        )
        batch_value = sum((b.cost_price or 0) * b.quantity_remaining for b in batches)

        # Also count pack instance value
        packs = (
            db.query(PackInstance)
            .filter(
                PackInstance.medicine_id == med.id,
                PackInstance.status.in_([PackStatus.SEALED, PackStatus.OPEN]),
                PackInstance.expiry_date >= today,
            )
            .all()
        )
        pack_value = sum((p.unit_cost or 0) * p.quantity_remaining for p in packs)

        total_value = batch_value + pack_value
        total_units = sum(b.quantity_remaining for b in batches) + sum(p.quantity_remaining for p in packs)

        cat = med.category or "Uncategorized"
        if cat not in categories:
            categories[cat] = {"category": cat, "total_value": 0.0, "total_units": 0, "item_count": 0}
        categories[cat]["total_value"] += total_value
        categories[cat]["total_units"] += total_units
        categories[cat]["item_count"] += 1

    breakdown = sorted(categories.values(), key=lambda x: x["total_value"], reverse=True)
    for row in breakdown:
        row["total_value"] = round(row["total_value"], 2)

    grand_total = sum(row["total_value"] for row in breakdown)
    grand_units = sum(row["total_units"] for row in breakdown)

    return {
        "grand_total_value": round(grand_total, 2),
        "grand_total_units": grand_units,
        "categories": breakdown,
    }
