"""
Write-Off Router
================
Endpoints for creating, listing, countersigning, and reporting on write-offs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.write_off import WriteOff, WriteOffStatus, ReasonCode
from app.models.pack_instance import PackInstance
from app.models.medicine import Medicine
from app.schemas.write_off import (
    WriteOffCreate,
    WriteOffRead,
    WriteOffReportRow,
    WriteOffReportResponse,
)
from app.services.writeoff import WriteOffService

router = APIRouter(prefix="/writeoffs", tags=["Write-Offs"])


def _enrich(wo: WriteOff, db: Session) -> WriteOffRead:
    data = WriteOffRead.model_validate(wo)
    if wo.medicine:
        data.medicine_name = wo.medicine.name
    if wo.initiated_by:
        data.initiated_by_username = wo.initiated_by.username
    if wo.countersigned_by:
        data.countersigned_by_username = wo.countersigned_by.username
    return data


@router.post("/", response_model=WriteOffRead, status_code=201)
def create_writeoff(
    payload: WriteOffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate a write-off. Controlled drugs go to pending_countersign state."""
    wo = WriteOffService.create(
        pack_instance_id=payload.pack_instance_id,
        quantity=payload.quantity,
        reason_code=payload.reason_code,
        notes=payload.notes,
        user_id=current_user.id,
        db=db,
    )
    return _enrich(wo, db)


@router.get("/", response_model=List[WriteOffRead])
def list_writeoffs(
    medicine_id: Optional[int] = None,
    status: Optional[str] = None,
    reason_code: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(WriteOff)
    if medicine_id:
        q = q.filter(WriteOff.medicine_id == medicine_id)
    if status:
        q = q.filter(WriteOff.status == status)
    if reason_code:
        q = q.filter(WriteOff.reason_code == reason_code)
    writeoffs = q.order_by(WriteOff.initiated_at.desc()).limit(limit).all()
    return [_enrich(wo, db) for wo in writeoffs]


@router.get("/pending-countersign", response_model=List[WriteOffRead])
def pending_countersign(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Outstanding countersign report — only pharmacist/admin roles."""
    if current_user.role not in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Pharmacist or Admin role required")

    now = datetime.utcnow()
    writeoffs = (
        db.query(WriteOff)
        .filter(WriteOff.status == WriteOffStatus.PENDING_COUNTERSIGN)
        .order_by(WriteOff.initiated_at.asc())
        .all()
    )
    return [_enrich(wo, db) for wo in writeoffs]


@router.get("/report", response_model=WriteOffReportResponse)
def writeoff_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    """Cost report grouped by reason_code and product for a date range."""
    writeoffs = (
        db.query(WriteOff)
        .filter(
            WriteOff.status == WriteOffStatus.FINALISED,
            WriteOff.initiated_at >= datetime.combine(start_date, datetime.min.time()),
            WriteOff.initiated_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .all()
    )

    # Group by (reason_code, medicine_id)
    groups = {}
    for wo in writeoffs:
        key = (wo.reason_code.value if hasattr(wo.reason_code, 'value') else wo.reason_code, wo.medicine_id)
        if key not in groups:
            med = wo.medicine
            groups[key] = {
                "reason_code": key[0],
                "medicine_id": wo.medicine_id,
                "medicine_name": med.name if med else "Unknown",
                "total_quantity": 0,
                "total_value": 0.0,
                "count": 0,
                "cost_unavailable_count": 0,
            }
        g = groups[key]
        g["total_quantity"] += wo.quantity
        g["count"] += 1
        if wo.cost_unavailable:
            g["cost_unavailable_count"] += 1
        elif wo.calculated_value is not None:
            g["total_value"] += wo.calculated_value

    rows = []
    for g in groups.values():
        total_val = g["total_value"] if g["total_value"] > 0 else None
        rows.append(WriteOffReportRow(
            reason_code=g["reason_code"],
            medicine_id=g["medicine_id"],
            medicine_name=g["medicine_name"],
            total_quantity=g["total_quantity"],
            total_value=total_val,
            count=g["count"],
            cost_unavailable_count=g["cost_unavailable_count"],
        ))

    grand_value = sum(r.total_value for r in rows if r.total_value is not None) or None
    grand_qty = sum(r.total_quantity for r in rows)

    return WriteOffReportResponse(
        start_date=str(start_date),
        end_date=str(end_date),
        rows=rows,
        grand_total_value=grand_value,
        grand_total_quantity=grand_qty,
    )


@router.get("/{writeoff_id}", response_model=WriteOffRead)
def get_writeoff(writeoff_id: int, db: Session = Depends(get_db)):
    wo = db.query(WriteOff).filter(WriteOff.id == writeoff_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Write-off not found")
    return _enrich(wo, db)


@router.post("/{writeoff_id}/countersign", response_model=WriteOffRead)
def countersign(
    writeoff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Countersign a pending controlled-drug write-off."""
    wo = WriteOffService.countersign(
        writeoff_id=writeoff_id,
        countersigner_user_id=current_user.id,
        db=db,
    )
    return _enrich(wo, db)
