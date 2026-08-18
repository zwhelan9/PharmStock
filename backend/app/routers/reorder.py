"""
Reorder Recommendation Engine (FR-3)
======================================
Calculates recommended order quantities per medicine based on:
  predicted demand + safety stock − current stock

Groups recommendations by supplier for streamlined ordering.
Supports approve/override workflow and CSV export.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta, datetime
import csv
import io

from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.models.sale import Sale
from app.models.user import User
from app.models.pack_instance import PackInstance, PackStatus
from app.core.config import settings

router = APIRouter(prefix="/reorder", tags=["Reorder Recommendations"])


def _get_on_hand(medicine_id: int, db: Session) -> int:
    """On-hand from pack instances (preferred) or batch fallback."""
    today = date.today()
    pack_qty = (
        db.query(func.sum(PackInstance.quantity_remaining))
        .filter(
            PackInstance.medicine_id == medicine_id,
            PackInstance.status.in_([PackStatus.SEALED, PackStatus.OPEN]),
            PackInstance.expiry_date >= today,
        )
        .scalar()
    )
    if pack_qty is not None:
        return pack_qty
    return (
        db.query(func.sum(Batch.quantity_remaining))
        .filter(Batch.medicine_id == medicine_id, Batch.is_active == True)
        .scalar() or 0
    )


def _avg_daily_demand(medicine_id: int, days: int, db: Session) -> float:
    """Average daily sales over last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    total = (
        db.query(func.sum(Sale.quantity))
        .filter(Sale.medicine_id == medicine_id, Sale.sale_date >= cutoff)
        .scalar() or 0
    )
    return total / max(days, 1)


@router.get("/recommendations")
def get_recommendations(
    horizon_days: int = Query(14, description="Forecast horizon for demand calculation"),
    safety_days: int = Query(7, description="Safety stock expressed as days of cover"),
    db: Session = Depends(get_db),
):
    """
    Generate reorder recommendations for all medicines.
    Formula: recommended_qty = (predicted_demand + safety_stock) - current_stock
    Where safety_stock = avg_daily_demand × safety_days
    """
    medicines = db.query(Medicine).order_by(Medicine.name).all()
    recommendations = []

    for med in medicines:
        on_hand = _get_on_hand(med.id, db)
        avg_daily = _avg_daily_demand(med.id, 90, db)  # Use 90-day average
        predicted_demand = round(avg_daily * horizon_days)
        safety_stock = round(avg_daily * safety_days)

        recommended_qty = max(0, (predicted_demand + safety_stock) - on_hand)

        # Round up to pack size / reorder quantity if needed
        if recommended_qty > 0 and med.reorder_quantity > 0:
            # Round up to nearest reorder_quantity multiple
            multiples = -(-recommended_qty // med.reorder_quantity)  # ceiling division
            recommended_qty = multiples * med.reorder_quantity

        # Determine urgency
        days_of_stock = round(on_hand / avg_daily) if avg_daily > 0 else 999
        if days_of_stock <= 3:
            urgency = "critical"
        elif days_of_stock <= 7:
            urgency = "high"
        elif days_of_stock <= 14:
            urgency = "medium"
        else:
            urgency = "low"

        recommendations.append({
            "medicine_id": med.id,
            "medicine_name": med.name,
            "category": med.category,
            "supplier": med.supplier,
            "unit": med.unit,
            "current_stock": on_hand,
            "reorder_level": med.reorder_level,
            "avg_daily_demand": round(avg_daily, 1),
            "predicted_demand": predicted_demand,
            "safety_stock": safety_stock,
            "recommended_qty": recommended_qty,
            "days_of_stock_remaining": days_of_stock,
            "urgency": urgency,
            "needs_reorder": recommended_qty > 0 or on_hand <= med.reorder_level,
        })

    # Sort: critical first, then by days_of_stock ascending
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: (urgency_order.get(r["urgency"], 9), r["days_of_stock_remaining"]))

    return {
        "generated_at": datetime.now().isoformat(),
        "horizon_days": horizon_days,
        "safety_days": safety_days,
        "total_items": len(recommendations),
        "needs_reorder_count": sum(1 for r in recommendations if r["needs_reorder"]),
        "recommendations": recommendations,
    }


@router.get("/by-supplier")
def recommendations_by_supplier(
    horizon_days: int = Query(14),
    safety_days: int = Query(7),
    db: Session = Depends(get_db),
):
    """Group recommendations by supplier for streamlined ordering."""
    data = get_recommendations(horizon_days=horizon_days, safety_days=safety_days, db=db)
    reorder_items = [r for r in data["recommendations"] if r["needs_reorder"]]

    suppliers = {}
    for item in reorder_items:
        supplier = item["supplier"] or "Unknown Supplier"
        if supplier not in suppliers:
            suppliers[supplier] = {"supplier": supplier, "items": [], "total_items": 0}
        suppliers[supplier]["items"].append(item)
        suppliers[supplier]["total_items"] += 1

    return {
        "generated_at": data["generated_at"],
        "horizon_days": horizon_days,
        "safety_days": safety_days,
        "suppliers": list(suppliers.values()),
    }


@router.get("/export")
def export_csv(
    horizon_days: int = Query(14),
    safety_days: int = Query(7),
    db: Session = Depends(get_db),
):
    """Export reorder recommendations as CSV."""
    data = get_recommendations(horizon_days=horizon_days, safety_days=safety_days, db=db)
    reorder_items = [r for r in data["recommendations"] if r["needs_reorder"]]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Medicine", "Category", "Supplier", "Unit", "Current Stock",
        "Avg Daily Demand", "Predicted Demand", "Safety Stock",
        "Recommended Order Qty", "Days of Stock", "Urgency",
    ])
    for item in reorder_items:
        writer.writerow([
            item["medicine_name"], item["category"], item["supplier"],
            item["unit"], item["current_stock"], item["avg_daily_demand"],
            item["predicted_demand"], item["safety_stock"],
            item["recommended_qty"], item["days_of_stock_remaining"],
            item["urgency"],
        ])

    output.seek(0)
    today_str = date.today().isoformat()
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reorder_recommendations_{today_str}.csv"},
    )
