"""
Dispensing Integration Layer — Ingestion Service
==================================================
Validates incoming dispense event and stock snapshot data against the
data contract, deduplicates by event_id, quarantines malformed rows,
and logs every import run for audit.

Design principles (from spec):
- IL-1.1: Read-only — never writes back to source system
- IL-4.1.3: Reject and flag malformed rows, never silently drop
- NFR Idempotency: Re-importing same file must not double-count (event_id dedup)
- NFR Auditability: Every import run logged with counts
"""

from __future__ import annotations

import json
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.integration import ImportLog, StockSnapshot, QuarantinedRecord, DispenseEvent
from app.models.medicine import Medicine
from app.services.fefo import FEFOService, InsufficientStockError
from app.models.dispense_transaction import DispenseSource


# ── Schema Definitions ────────────────────────────────────────────────────────

DISPENSE_EVENT_REQUIRED = {"event_id", "timestamp", "product_code", "quantity_dispensed", "transaction_type"}
DISPENSE_EVENT_RECOMMENDED = {"pack_size", "batch_number", "is_controlled_drug"}

STOCK_SNAPSHOT_REQUIRED = {"product_code", "quantity_on_hand", "snapshot_timestamp"}
STOCK_SNAPSHOT_RECOMMENDED = {"batch_number", "expiry_date"}

VALID_TRANSACTION_TYPES = {"dispense", "return", "adjustment", "destruction"}


class IngestionResult:
    """Result of processing a single import."""

    def __init__(self):
        self.processed = 0
        self.rejected = 0
        self.deduplicated = 0
        self.errors: List[Dict[str, Any]] = []

    @property
    def total(self):
        return self.processed + self.rejected + self.deduplicated


class IngestionService:
    """Stateless service for importing dispense events and stock snapshots."""

    # ── Dispense Events ───────────────────────────────────────────────────────

    @classmethod
    def validate_dispense_row(cls, row: Dict[str, Any], row_num: int) -> Tuple[bool, Optional[str]]:
        """Validate a single dispense event row against the data contract."""
        # Check required fields
        missing = DISPENSE_EVENT_REQUIRED - set(row.keys())
        # Allow sku as alias for product_code
        if "product_code" in missing and "sku" in row:
            missing.discard("product_code")
        if missing:
            return False, f"Missing required fields: {', '.join(sorted(missing))}"

        # Validate event_id
        event_id = row.get("event_id", "").strip()
        if not event_id:
            return False, "event_id is empty"

        # Validate quantity
        try:
            qty = int(row["quantity_dispensed"])
            if qty < 1:
                return False, f"quantity_dispensed must be >= 1, got {qty}"
        except (ValueError, TypeError):
            return False, f"quantity_dispensed is not a valid integer: {row.get('quantity_dispensed')}"

        # Validate timestamp
        try:
            ts = row["timestamp"]
            if isinstance(ts, str):
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False, f"timestamp is not valid ISO format: {row.get('timestamp')}"

        # Validate transaction_type
        txn_type = row.get("transaction_type", "").strip().lower()
        if txn_type not in VALID_TRANSACTION_TYPES:
            return False, f"transaction_type '{txn_type}' not in {sorted(VALID_TRANSACTION_TYPES)}"

        # Validate product_code resolves (done later in processing, not here)
        product_code = row.get("product_code") or row.get("sku", "")
        if not str(product_code).strip():
            return False, "product_code/sku is empty"

        return True, None

    @classmethod
    def ingest_dispense_events(
        cls,
        rows: List[Dict[str, Any]],
        import_log: ImportLog,
        db: Session,
    ) -> IngestionResult:
        """
        Process a list of dispense event rows.
        - Validates each row
        - Deduplicates by event_id
        - Quarantines invalid rows
        - Creates DispenseEvent records for valid ones
        - Optionally triggers FEFO logic for 'dispense' type events
        """
        result = IngestionResult()

        for i, row in enumerate(rows):
            row_num = i + 1

            # Validate
            valid, error_msg = cls.validate_dispense_row(row, row_num)
            if not valid:
                cls._quarantine(row, row_num, error_msg, import_log, db)
                result.rejected += 1
                result.errors.append({"row": row_num, "error": error_msg})
                continue

            # Check deduplication
            event_id = row["event_id"].strip()
            existing = db.query(DispenseEvent).filter(DispenseEvent.event_id == event_id).first()
            if existing:
                result.deduplicated += 1
                continue

            # Resolve product
            product_code = str(row.get("product_code") or row.get("sku", "")).strip()
            medicine = cls._resolve_medicine(product_code, db)
            if not medicine:
                cls._quarantine(row, row_num, f"Unresolved product_code: {product_code}", import_log, db)
                result.rejected += 1
                result.errors.append({"row": row_num, "error": f"Unknown product: {product_code}"})
                continue

            # Parse fields
            ts_str = row["timestamp"]
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                ts = ts_str

            qty = int(row["quantity_dispensed"])
            txn_type = row.get("transaction_type", "dispense").strip().lower()
            is_cd = str(row.get("is_controlled_drug", "false")).lower() in ("true", "1", "yes")
            pack_size = int(row["pack_size"]) if row.get("pack_size") else None
            batch_num = row.get("batch_number")

            # Create event record
            event = DispenseEvent(
                event_id=event_id,
                timestamp=ts,
                medicine_id=medicine.id,
                sku=product_code,
                quantity_dispensed=qty,
                pack_size=pack_size,
                batch_number=batch_num,
                is_controlled_drug=is_cd,
                transaction_type=txn_type,
                import_log_id=import_log.id,
            )
            db.add(event)

            # For dispense-type events, also trigger FEFO deduction if packs exist
            if txn_type == "dispense":
                try:
                    FEFOService.apply_dispense(
                        medicine_id=medicine.id,
                        quantity=qty,
                        db=db,
                        source=DispenseSource.TOUCHSTORE_RX,
                        touchstore_ref=event_id,
                    )
                except InsufficientStockError:
                    # Don't reject — the event is still valid, just can't deduct from packs
                    pass
                except Exception:
                    pass

            result.processed += 1

        db.commit()
        return result

    # ── Stock Snapshots ───────────────────────────────────────────────────────

    @classmethod
    def validate_snapshot_row(cls, row: Dict[str, Any], row_num: int) -> Tuple[bool, Optional[str]]:
        """Validate a stock snapshot row."""
        missing = STOCK_SNAPSHOT_REQUIRED - set(row.keys())
        if "product_code" in missing and "sku" in row:
            missing.discard("product_code")
        if missing:
            return False, f"Missing required fields: {', '.join(sorted(missing))}"

        try:
            qty = int(row["quantity_on_hand"])
            if qty < 0:
                return False, f"quantity_on_hand cannot be negative: {qty}"
        except (ValueError, TypeError):
            return False, f"quantity_on_hand is not a valid integer: {row.get('quantity_on_hand')}"

        try:
            ts = row["snapshot_timestamp"]
            if isinstance(ts, str):
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False, f"snapshot_timestamp is not valid ISO format: {row.get('snapshot_timestamp')}"

        return True, None

    @classmethod
    def ingest_stock_snapshots(
        cls,
        rows: List[Dict[str, Any]],
        import_log: ImportLog,
        db: Session,
    ) -> IngestionResult:
        """Process stock snapshot rows."""
        result = IngestionResult()

        for i, row in enumerate(rows):
            row_num = i + 1

            valid, error_msg = cls.validate_snapshot_row(row, row_num)
            if not valid:
                cls._quarantine(row, row_num, error_msg, import_log, db)
                result.rejected += 1
                result.errors.append({"row": row_num, "error": error_msg})
                continue

            product_code = str(row.get("product_code") or row.get("sku", "")).strip()
            medicine = cls._resolve_medicine(product_code, db)
            if not medicine:
                cls._quarantine(row, row_num, f"Unresolved product_code: {product_code}", import_log, db)
                result.rejected += 1
                result.errors.append({"row": row_num, "error": f"Unknown product: {product_code}"})
                continue

            ts_str = row["snapshot_timestamp"]
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                ts = ts_str

            from datetime import date as date_type
            expiry = None
            if row.get("expiry_date"):
                try:
                    expiry = date_type.fromisoformat(str(row["expiry_date"]))
                except ValueError:
                    pass

            snapshot = StockSnapshot(
                medicine_id=medicine.id,
                sku=product_code,
                quantity_on_hand=int(row["quantity_on_hand"]),
                batch_number=row.get("batch_number"),
                expiry_date=expiry,
                snapshot_timestamp=ts,
                import_log_id=import_log.id,
            )
            db.add(snapshot)
            result.processed += 1

        db.commit()
        return result

    # ── CSV Parsing ───────────────────────────────────────────────────────────

    @classmethod
    def parse_csv(cls, content: str) -> List[Dict[str, Any]]:
        """Parse CSV content into list of dicts."""
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @classmethod
    def _resolve_medicine(cls, product_code: str, db: Session) -> Optional[Medicine]:
        """Try to resolve a product_code to a Medicine. Tries ID, barcode, then name."""
        # Try as integer ID
        try:
            med_id = int(product_code)
            med = db.query(Medicine).filter(Medicine.id == med_id).first()
            if med:
                return med
        except ValueError:
            pass

        # Try barcode
        med = db.query(Medicine).filter(Medicine.barcode == product_code).first()
        if med:
            return med

        # Try exact name match
        med = db.query(Medicine).filter(Medicine.name == product_code).first()
        return med

    @classmethod
    def _quarantine(
        cls,
        row: Dict[str, Any],
        row_num: int,
        reason: str,
        import_log: ImportLog,
        db: Session,
    ) -> None:
        """Store a rejected row in quarantine for review."""
        record = QuarantinedRecord(
            import_log_id=import_log.id,
            row_number=row_num,
            raw_data=json.dumps(row, default=str),
            rejection_reason=reason,
        )
        db.add(record)
