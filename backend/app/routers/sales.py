from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.models.sale import Sale
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.stock_log import StockLog, ChangeType
from app.schemas.sale import SaleCreate, SaleRead

router = APIRouter(prefix="/sales", tags=["Sales"])


def _sale_to_read(s: Sale, db: Session) -> SaleRead:
    med = db.query(Medicine.name).filter(Medicine.id == s.medicine_id).first()
    return SaleRead(
        id=s.id,
        medicine_id=s.medicine_id,
        batch_id=s.batch_id,
        quantity=s.quantity,
        unit_price=s.unit_price,
        total_price=s.total_price,
        customer_ref=s.customer_ref,
        prescription_ref=s.prescription_ref,
        is_prescription=s.is_prescription,
        served_by=s.served_by,
        notes=s.notes,
        sale_date=s.sale_date,
        medicine_name=med[0] if med else None,
    )


@router.get("/", response_model=List[SaleRead])
def list_sales(
    medicine_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(Sale)
    if medicine_id:
        query = query.filter(Sale.medicine_id == medicine_id)
    if date_from:
        query = query.filter(Sale.sale_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Sale.sale_date <= datetime.combine(date_to, datetime.max.time()))

    sales = query.order_by(Sale.sale_date.desc()).offset(offset).limit(limit).all()
    return [_sale_to_read(s, db) for s in sales]


@router.get("/summary/daily")
def daily_sales_summary(
    days: int = Query(30, ge=1, le=365),
    medicine_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns daily total units sold for the last N days."""
    since = datetime.combine(date.today() - timedelta(days=days), datetime.min.time())
    query = db.query(
        func.date(Sale.sale_date).label("sale_day"),
        func.sum(Sale.quantity).label("total_qty"),
        func.sum(Sale.total_price).label("total_revenue"),
        func.count(Sale.id).label("transaction_count"),
    ).filter(Sale.sale_date >= since)

    if medicine_id:
        query = query.filter(Sale.medicine_id == medicine_id)

    rows = query.group_by(func.date(Sale.sale_date)).order_by("sale_day").all()
    return [
        {
            "date": r.sale_day,
            "total_qty": r.total_qty or 0,
            "total_revenue": round(r.total_revenue or 0, 2),
            "transaction_count": r.transaction_count,
        }
        for r in rows
    ]


@router.get("/summary/by-medicine")
def sales_by_medicine(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.combine(date.today() - timedelta(days=days), datetime.min.time())
    rows = (
        db.query(
            Sale.medicine_id,
            Medicine.name,
            func.sum(Sale.quantity).label("total_qty"),
            func.sum(Sale.total_price).label("total_revenue"),
        )
        .join(Medicine, Medicine.id == Sale.medicine_id)
        .filter(Sale.sale_date >= since)
        .group_by(Sale.medicine_id, Medicine.name)
        .order_by(func.sum(Sale.quantity).desc())
        .all()
    )
    return [
        {
            "medicine_id": r.medicine_id,
            "medicine_name": r.name,
            "total_qty": r.total_qty or 0,
            "total_revenue": round(r.total_revenue or 0, 2),
        }
        for r in rows
    ]


@router.post("/", response_model=SaleRead, status_code=201)
def record_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    medicine = db.query(Medicine).filter(Medicine.id == payload.medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # Determine batch (FEFO if not specified)
    batch = None
    if payload.batch_id:
        batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
    else:
        # Pick earliest-expiring batch with sufficient stock (FEFO)
        batch = (
            db.query(Batch)
            .filter(
                Batch.medicine_id == payload.medicine_id,
                Batch.is_active == True,
                Batch.quantity_remaining >= payload.quantity,
                Batch.expiry_date >= date.today(),
            )
            .order_by(Batch.expiry_date.asc())
            .first()
        )
        if not batch:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock or no valid batch available",
            )

    if batch.quantity_remaining < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity in this batch")

    unit_price = payload.unit_price or medicine.selling_price or 0.0
    total_price = unit_price * payload.quantity

    sale = Sale(
        medicine_id=payload.medicine_id,
        batch_id=batch.id,
        quantity=payload.quantity,
        unit_price=unit_price,
        total_price=total_price,
        customer_ref=payload.customer_ref,
        prescription_ref=payload.prescription_ref,
        is_prescription=payload.is_prescription,
        served_by=payload.served_by,
        notes=payload.notes,
        sale_date=payload.sale_date or datetime.utcnow(),
    )
    db.add(sale)

    # Deduct from batch
    stock_before_batch = batch.quantity_remaining
    batch.quantity_remaining -= payload.quantity
    if batch.quantity_remaining <= 0:
        batch.is_active = False

    # Compute total medicine stock
    all_batches = (
        db.query(Batch)
        .filter(Batch.medicine_id == payload.medicine_id, Batch.is_active == True)
        .all()
    )
    total_before = sum(b.quantity_remaining for b in all_batches) + payload.quantity
    total_after = total_before - payload.quantity

    log = StockLog(
        medicine_id=payload.medicine_id,
        batch_id=batch.id,
        change_type=ChangeType.SALE,
        quantity=-payload.quantity,
        stock_before=total_before,
        stock_after=total_after,
        notes=f"Sale of {payload.quantity} units",
    )
    db.add(log)
    db.commit()
    db.refresh(sale)
    return _sale_to_read(sale, db)


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    s = db.query(Sale).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sale not found")
    return _sale_to_read(s, db)
