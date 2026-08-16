from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.schemas.medicine import MedicineCreate, MedicineUpdate, MedicineRead, MedicineListItem
from app.core.config import settings

router = APIRouter(prefix="/medicines", tags=["Medicines"])


def _enrich(medicine: Medicine, db: Session) -> dict:
    """Compute aggregated stock and expiry fields for a medicine."""
    today = date.today()
    watch_date = today + timedelta(days=settings.EXPIRY_WATCH_DAYS)

    active_batches = (
        db.query(Batch)
        .filter(Batch.medicine_id == medicine.id, Batch.is_active == True)
        .all()
    )

    total_stock = sum(b.quantity_remaining for b in active_batches)
    expiring_soon = sum(
        1 for b in active_batches
        if b.expiry_date <= watch_date and b.expiry_date >= today
    )

    return {
        "total_stock": total_stock,
        "is_low_stock": total_stock <= medicine.reorder_level,
        "expiring_soon_count": expiring_soon,
    }


# ── Static routes MUST come before /{medicine_id} ────────────────────────────

@router.get("/categories/list")
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(Medicine.category).distinct().order_by(Medicine.category).all()
    return [r[0] for r in rows]


@router.get("/", response_model=List[MedicineListItem])
def list_medicines(
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Medicine)
    if category:
        query = query.filter(Medicine.category == category)
    if search:
        query = query.filter(Medicine.name.ilike(f"%{search}%"))

    medicines = query.order_by(Medicine.name).all()
    result = []
    for m in medicines:
        try:
            enriched = _enrich(m, db)
        except Exception:
            enriched = {"total_stock": 0, "is_low_stock": False, "expiring_soon_count": 0}
        if low_stock_only and not enriched["is_low_stock"]:
            continue
        item = MedicineListItem(
            id=m.id,
            name=m.name,
            category=m.category,
            unit=m.unit,
            selling_price=m.selling_price,
            reorder_level=m.reorder_level,
            **enriched,
        )
        result.append(item)
    return result


# ── Parameterised routes AFTER static ones ───────────────────────────────────

@router.get("/{medicine_id}", response_model=MedicineRead)
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    enriched = _enrich(m, db)
    data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    data.update(enriched)
    return MedicineRead(**data)


@router.post("/", response_model=MedicineRead, status_code=201)
def create_medicine(payload: MedicineCreate, db: Session = Depends(get_db)):
    existing = db.query(Medicine).filter(Medicine.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Medicine with this name already exists")
    m = Medicine(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    enriched = _enrich(m, db)
    data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    data.update(enriched)
    return MedicineRead(**data)


@router.patch("/{medicine_id}", response_model=MedicineRead)
def update_medicine(medicine_id: int, payload: MedicineUpdate, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    enriched = _enrich(m, db)
    data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    data.update(enriched)
    return MedicineRead(**data)


@router.delete("/{medicine_id}", status_code=204)
def delete_medicine(medicine_id: int, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    db.delete(m)
    db.commit()
