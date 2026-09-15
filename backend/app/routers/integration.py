"""
Dispensing Integration Layer Router
=====================================
File upload, reconciliation, sync status, and import audit trail.
"""

import csv
import io
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.medicine import Medicine
from app.models.integration import ImportLog, StockSnapshot, QuarantinedRecord, DispenseEvent
from app.models.pack_instance import PackInstance, PackStatus
from app.models.batch import Batch
from app.services.ingestion import IngestionService
from app.services.fefo import FEFOService

router = APIRouter(prefix="/integration", tags=["Integration Layer"])


# ── File Upload ───────────────────────────────────────────────────────────────

@router.post("/import/dispense-events")
async def import_dispense_events(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CSV of dispense events matching the data contract.
    Expected columns: event_id, timestamp, product_code, quantity_dispensed,
                      transaction_type, [pack_size, batch_number, is_controlled_drug]
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted")

    content = (await file.read()).decode("utf-8-sig")

    # Create import log
    log = ImportLog(
        source="file_upload",
        source_filename=file.filename,
        import_type="dispense_events",
        status="running",
        imported_by_user_id=current_user.id,
    )
    db.add(log)
    db.flush()

    try:
        rows = IngestionService.parse_csv(content)
        log.total_records = len(rows)

        result = IngestionService.ingest_dispense_events(rows, log, db)

        log.records_processed = result.processed
        log.records_rejected = result.rejected
        log.records_deduplicated = result.deduplicated
        log.status = "completed"
        log.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    db.commit()
    db.refresh(log)

    return {
        "import_log_id": log.id,
        "status": log.status,
        "total_records": log.total_records,
        "processed": log.records_processed,
        "rejected": log.records_rejected,
        "deduplicated": log.records_deduplicated,
        "errors": result.errors[:20],  # Cap at 20 for response size
    }


@router.post("/import/stock-snapshot")
async def import_stock_snapshot(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CSV stock snapshot from the source system.
    Expected columns: product_code, quantity_on_hand, snapshot_timestamp,
                      [batch_number, expiry_date]
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted")

    content = (await file.read()).decode("utf-8-sig")

    log = ImportLog(
        source="file_upload",
        source_filename=file.filename,
        import_type="stock_snapshot",
        status="running",
        imported_by_user_id=current_user.id,
    )
    db.add(log)
    db.flush()

    try:
        rows = IngestionService.parse_csv(content)
        log.total_records = len(rows)

        result = IngestionService.ingest_stock_snapshots(rows, log, db)

        log.records_processed = result.processed
        log.records_rejected = result.rejected
        log.records_deduplicated = result.deduplicated
        log.status = "completed"
        log.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    db.commit()
    db.refresh(log)

    return {
        "import_log_id": log.id,
        "status": log.status,
        "total_records": log.total_records,
        "processed": log.records_processed,
        "rejected": log.records_rejected,
        "deduplicated": log.records_deduplicated,
        "errors": result.errors[:20],
    }


# ── Reconciliation ───────────────────────────────────────────────────────────

@router.get("/reconciliation")
def run_reconciliation(
    tolerance_pct: float = Query(2.0, description="% tolerance before flagging discrepancy"),
    db: Session = Depends(get_db),
):
    """
    IL-5.1–5.4: Compare calculated on-hand vs latest stock snapshot.
    Flags SKUs where divergence exceeds tolerance.
    """
    today = date.today()

    # Get latest snapshot per medicine
    subq = (
        db.query(
            StockSnapshot.medicine_id,
            func.max(StockSnapshot.snapshot_timestamp).label("latest_ts"),
        )
        .group_by(StockSnapshot.medicine_id)
        .subquery()
    )

    latest_snapshots = (
        db.query(StockSnapshot)
        .join(subq, (StockSnapshot.medicine_id == subq.c.medicine_id) & (StockSnapshot.snapshot_timestamp == subq.c.latest_ts))
        .all()
    )

    if not latest_snapshots:
        return {
            "status": "no_snapshots",
            "message": "No stock snapshots available for reconciliation",
            "discrepancies": [],
            "matches": 0,
        }

    discrepancies = []
    matches = 0

    for snap in latest_snapshots:
        system_qty = FEFOService.get_on_hand(snap.medicine_id, db)
        # Fallback to batch if no pack instances
        if system_qty == 0:
            system_qty = (
                db.query(func.sum(Batch.quantity_remaining))
                .filter(Batch.medicine_id == snap.medicine_id, Batch.is_active == True)
                .scalar() or 0
            )

        source_qty = snap.quantity_on_hand
        diff = abs(system_qty - source_qty)

        # Calculate tolerance
        base = max(system_qty, source_qty, 1)
        pct_diff = (diff / base) * 100

        if pct_diff > tolerance_pct:
            med = db.query(Medicine).filter(Medicine.id == snap.medicine_id).first()
            discrepancies.append({
                "medicine_id": snap.medicine_id,
                "medicine_name": med.name if med else f"#{snap.medicine_id}",
                "system_on_hand": system_qty,
                "source_on_hand": source_qty,
                "difference": system_qty - source_qty,
                "difference_pct": round(pct_diff, 1),
                "snapshot_timestamp": snap.snapshot_timestamp.isoformat() if snap.snapshot_timestamp else None,
                "status": "discrepancy",
            })
        else:
            matches += 1

    discrepancies.sort(key=lambda d: abs(d["difference"]), reverse=True)

    return {
        "status": "completed",
        "tolerance_pct": tolerance_pct,
        "total_checked": len(latest_snapshots),
        "matches": matches,
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
    }


# ── Data Freshness / Sync Status ─────────────────────────────────────────────

@router.get("/sync-status")
def sync_status(db: Session = Depends(get_db)):
    """
    Returns data freshness information:
    - Last successful import timestamp
    - Last reconciliation result
    - Staleness warning if > 24 hours since last sync
    """
    # Last successful import
    last_import = (
        db.query(ImportLog)
        .filter(ImportLog.status == "completed")
        .order_by(ImportLog.completed_at.desc())
        .first()
    )

    # Last dispense event timestamp
    last_event = (
        db.query(func.max(DispenseEvent.timestamp))
        .scalar()
    )

    # Import history (last 10)
    recent_imports = (
        db.query(ImportLog)
        .order_by(ImportLog.started_at.desc())
        .limit(10)
        .all()
    )

    now = datetime.now(timezone.utc)
    stale_threshold = timedelta(hours=24)

    last_sync_time = last_import.completed_at if last_import else None
    is_stale = False
    hours_since_sync = None

    if last_sync_time:
        # Handle timezone-naive datetimes
        if last_sync_time.tzinfo is None:
            last_sync_time = last_sync_time.replace(tzinfo=timezone.utc)
        delta = now - last_sync_time
        hours_since_sync = round(delta.total_seconds() / 3600, 1)
        is_stale = delta > stale_threshold

    return {
        "last_successful_sync": last_sync_time.isoformat() if last_sync_time else None,
        "hours_since_last_sync": hours_since_sync,
        "is_stale": is_stale,
        "stale_threshold_hours": 24,
        "last_dispense_event": last_event.isoformat() if last_event else None,
        "total_imports": db.query(func.count(ImportLog.id)).scalar(),
        "total_dispense_events": db.query(func.count(DispenseEvent.id)).scalar(),
        "total_snapshots": db.query(func.count(StockSnapshot.id)).scalar(),
        "recent_imports": [
            {
                "id": imp.id,
                "source": imp.source,
                "import_type": imp.import_type,
                "filename": imp.source_filename,
                "status": imp.status,
                "started_at": imp.started_at.isoformat() if imp.started_at else None,
                "total_records": imp.total_records,
                "processed": imp.records_processed,
                "rejected": imp.records_rejected,
                "deduplicated": imp.records_deduplicated,
            }
            for imp in recent_imports
        ],
    }


# ── Import History & Quarantine ───────────────────────────────────────────────

@router.get("/import-logs")
def list_import_logs(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List all import runs for audit."""
    logs = db.query(ImportLog).order_by(ImportLog.started_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "source": log.source,
            "source_filename": log.source_filename,
            "import_type": log.import_type,
            "status": log.status,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "total_records": log.total_records,
            "records_processed": log.records_processed,
            "records_rejected": log.records_rejected,
            "records_deduplicated": log.records_deduplicated,
            "error_message": log.error_message,
        }
        for log in logs
    ]


@router.get("/quarantined")
def list_quarantined(
    import_log_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """List quarantined (rejected) records for review."""
    q = db.query(QuarantinedRecord)
    if import_log_id:
        q = q.filter(QuarantinedRecord.import_log_id == import_log_id)
    records = q.order_by(QuarantinedRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "import_log_id": r.import_log_id,
            "row_number": r.row_number,
            "raw_data": r.raw_data,
            "rejection_reason": r.rejection_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
