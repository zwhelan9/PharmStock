# Design Document — Pack-Level Stock Tracking

## Overview

This design extends PharmStock with four capabilities: (1) physical pack instance tracking, (2) FEFO-based dispensing, (3) formal write-off recording with controlled-drug countersign, and (4) TouchStore Rx reconciliation. All changes layer on top of the existing FastAPI + SQLAlchemy + SQLite backend and React + Tailwind frontend without removing existing data.

---

## Architecture

```mermaid
graph TD
    subgraph Frontend
        UI_Packs[Pack Inventory Page]
        UI_Dispense[Dispense Modal]
        UI_WriteOff[Write-Off Page]
        UI_Expiry[Expiry Alerts Page enhanced]
        UI_Reports[Write-Off Report]
    end

    subgraph Backend API
        R_Packs[/api/v1/packs]
        R_Dispense[/api/v1/dispense]
        R_WriteOff[/api/v1/writeoffs]
        R_TouchStore[/api/v1/touchstore/import]
        R_Predictions[/api/v1/predictions - updated]
    end

    subgraph Services
        FEFO[FEFOService]
        WriteOffSvc[WriteOffService]
    end

    subgraph Models
        PackInstance
        DispenseTransaction
        DispenseLineItem
        WriteOff
    end

    UI_Packs --> R_Packs
    UI_Dispense --> R_Dispense
    UI_WriteOff --> R_WriteOff
    R_Dispense --> FEFO
    R_WriteOff --> WriteOffSvc
    R_TouchStore --> FEFO
    FEFO --> PackInstance
    WriteOffSvc --> WriteOff
    R_Predictions --> PackInstance
```

---

## Data Models

### PackInstance

Represents one physical pack or box. Linked to `Medicine` directly (not `Batch`, which remains for historical stock-in records).

```
pack_instances
├── id                  INTEGER PK
├── medicine_id         INTEGER FK → medicines.id  NOT NULL  INDEX
├── batch_id            INTEGER FK → batches.id    NULLABLE  (links to delivery batch)
├── batch_number        VARCHAR(100)  NOT NULL
├── lot_number          VARCHAR(100)  NULLABLE
├── expiry_date         DATE  NOT NULL  INDEX
├── quantity_received   INTEGER  NOT NULL  (≥ 1)
├── quantity_remaining  INTEGER  NOT NULL
├── unit_cost           FLOAT  NULLABLE  (cost per unit from invoice)
├── status              ENUM('sealed','open','empty')  NOT NULL  DEFAULT 'sealed'  INDEX
├── date_opened         DATE  NULLABLE
├── is_controlled_drug  BOOLEAN  DEFAULT FALSE
├── supplier_invoice    VARCHAR(100)  NULLABLE
├── notes               TEXT  NULLABLE
├── created_at          DATETIME  server_default=now()
└── updated_at          DATETIME  onupdate=now()
```

### DispenseTransaction

Replaces `Sale` for new dispense records. Existing `Sale` table is preserved for historical data and prediction engine.

```
dispense_transactions
├── id                  INTEGER PK
├── medicine_id         INTEGER FK → medicines.id  NOT NULL  INDEX
├── total_quantity      INTEGER  NOT NULL
├── source              ENUM('manual','touchstore_rx')  DEFAULT 'manual'
├── touchstore_ref      VARCHAR(100)  NULLABLE
├── prescription_ref    VARCHAR(100)  NULLABLE
├── served_by_user_id   INTEGER FK → users.id  NULLABLE
├── notes               TEXT  NULLABLE
├── dispense_date       DATETIME  NOT NULL  INDEX
└── created_at          DATETIME  server_default=now()
```

### DispenseLineItem

One row per pack instance touched by a dispense transaction.

```
dispense_line_items
├── id                     INTEGER PK
├── dispense_transaction_id INTEGER FK → dispense_transactions.id  NOT NULL  INDEX
├── pack_instance_id        INTEGER FK → pack_instances.id  NOT NULL
├── quantity_deducted       INTEGER  NOT NULL
└── pack_status_after       ENUM('open','empty')  NOT NULL
```

### WriteOff

```
write_offs
├── id                  INTEGER PK
├── pack_instance_id    INTEGER FK → pack_instances.id  NOT NULL  INDEX
├── medicine_id         INTEGER FK → medicines.id  NOT NULL  INDEX
├── quantity            INTEGER  NOT NULL  (1 ≤ qty ≤ pack_instance.quantity_remaining at time of submission)
├── reason_code         ENUM('damaged','expired','spillage_contamination',
│                            'short_dated_return_to_supplier','dispensing_error',
│                            'theft_loss','recall')  NOT NULL
├── notes               TEXT  NULLABLE  (max 500 chars enforced in schema)
├── calculated_value    FLOAT  NULLABLE  (qty × unit_cost; NULL if no unit_cost)
├── cost_unavailable    BOOLEAN  NOT NULL  DEFAULT FALSE
├── status              ENUM('pending_countersign','finalised')  DEFAULT 'finalised'
├── initiated_by_user_id INTEGER FK → users.id  NOT NULL
├── initiated_at        DATETIME  NOT NULL
├── countersigned_by_user_id INTEGER FK → users.id  NULLABLE
├── countersigned_at    DATETIME  NULLABLE
├── countersign_deadline DATETIME  NULLABLE  (initiated_at + configurable window)
└── created_at          DATETIME  server_default=now()
```

### ReconciliationAdjustment

```
reconciliation_adjustments
├── id                  INTEGER PK
├── medicine_id         INTEGER FK → medicines.id  NOT NULL
├── quantity_before     INTEGER  NOT NULL
├── quantity_after      INTEGER  NOT NULL
├── reason              TEXT  NOT NULL  (min 1 char)
├── adjusted_by_user_id INTEGER FK → users.id  NOT NULL
├── touchstore_reported INTEGER  NULLABLE
└── created_at          DATETIME  server_default=now()
```

---

## Service Layer

### FEFOService (`app/services/fefo.py`)

```
class FEFOService:
    select_packs(medicine_id, quantity, db) -> List[Tuple[PackInstance, int]]
        # Returns ordered list of (pack, qty_to_deduct) pairs
        # Algorithm:
        #   1. Query open packs for medicine, order by expiry_date ASC, id ASC
        #   2. Fill from open packs until quantity satisfied
        #   3. If still remaining, query sealed packs, order by expiry_date ASC, id ASC
        #   4. Open first sealed pack (set status='open', date_opened=today)
        #   5. Continue until fulfilled or raise InsufficientStockError
        # Pure function — does NOT write to DB (router commits after validation)

    apply_dispense(medicine_id, quantity, served_by_user_id, source, ref, db) -> DispenseTransaction
        # Calls select_packs, creates DispenseTransaction + DispenseLineItems,
        # updates PackInstance quantities and statuses, commits

    get_on_hand(medicine_id, db) -> int
        # SUM(quantity_remaining) WHERE status IN ('sealed','open')
        #   AND expiry_date >= today
```

### WriteOffService (`app/services/writeoff.py`)

```
class WriteOffService:
    create(pack_instance_id, qty, reason_code, notes, user_id, db) -> WriteOff
        # Validates qty ≤ remaining, reason_code in enum
        # If medicine.is_controlled_drug: status='pending_countersign', set deadline
        # Else: status='finalised', deduct qty immediately

    countersign(writeoff_id, countersigner_user_id, db) -> WriteOff
        # Validates: countersigner ≠ initiator, countersigner role in (admin, staff)
        # Sets status='finalised', records countersigner + timestamp
        # Deducts quantity from PackInstance
```

---

## API Endpoints

### Pack Instances — `/api/v1/packs`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/packs/` | List all pack instances (filterable by medicine_id, status) |
| GET | `/packs/{id}` | Single pack instance |
| POST | `/packs/` | Create pack instance (delivery receipt) |
| PATCH | `/packs/{id}` | Update notes/quarantine flag |
| GET | `/packs/medicine/{medicine_id}/on-hand` | On-hand qty for a medicine |
| GET | `/packs/expiry-alerts` | Packs within alert window, sorted by status then date |

### Dispense — `/api/v1/dispense`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/dispense/` | Record a manual dispense (triggers FEFO) |
| GET | `/dispense/` | List dispense transactions |
| GET | `/dispense/{id}` | Transaction with line items |

### Write-Offs — `/api/v1/writeoffs`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/writeoffs/` | Initiate write-off |
| GET | `/writeoffs/` | List write-offs (filterable by status, medicine, reason) |
| GET | `/writeoffs/{id}` | Single write-off |
| POST | `/writeoffs/{id}/countersign` | Countersign a pending write-off |
| GET | `/writeoffs/report` | Cost report grouped by reason+product for date range |
| GET | `/writeoffs/pending-countersign` | Outstanding countersign report (pharmacist+ only) |

### TouchStore Rx — `/api/v1/touchstore`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/touchstore/import` | Import dispense event from TouchStore Rx |
| GET | `/touchstore/reconciliation-flags` | Products flagged for manual reconciliation |
| POST | `/touchstore/reconcile/{medicine_id}` | Submit reconciliation adjustment |

---

## Config Additions

New fields in `Settings`:

```python
# Pack / Write-Off
COUNTERSIGN_WINDOW_HOURS: int = 24        # configurable 1–168
COUNTERSIGN_WINDOW_MIN: int = 1
COUNTERSIGN_WINDOW_MAX: int = 168
WRITEOFF_LOSS_RATE_THRESHOLD: float = 0.1  # 10% of dispense volume in 30d triggers flag
TOUCHSTORE_QTY_TOLERANCE: int = 0          # units of tolerance (0–99)
PACK_EXPIRY_ALERT_DAYS: int = 90           # default alert window for pack expiry
```

---

## Prediction Engine Changes

`predictions.py` `_current_stock()` updates from `Batch.quantity_remaining` to `PackInstance.quantity_remaining` where `status IN ('sealed','open')` and `expiry_date >= today`.

`_get_sales_history()` continues to use `Sale` table for historical demand. New `DispenseTransaction` records feed in from a parallel query — both are unioned so the model sees a continuous demand signal.

Write-offs are excluded from demand signal. A `_get_loss_signal()` helper computes 30-day rolling write-off volume per medicine and attaches it as a non-forecast field.

---

## Frontend Pages

### Pack Inventory (`/packs`)
- Table of pack instances grouped by medicine
- Status badges: sealed (grey), open (blue), empty (faded)
- Inline "Receive Delivery" button → modal for creating pack instances
- "Dispense" button per medicine → FEFO dispense modal
- On-hand quantity badge per medicine

### Write-Offs (`/writeoffs`)
- List of write-offs with status, reason, value
- "New Write-Off" → select medicine → select pack instance → qty + reason form
- Pending countersign queue (pharmacist+ only)
- Cost report tab: date-range picker, grouped table, cost_unavailable callout

### Expiry Alerts (enhanced `/expiry`)
- Existing expiry alerts remain
- New "Pack Level" tab showing individual pack instances near expiry
- Expired-but-not-written-off packs highlighted with "Write-Off Required" prompt

---

## Property-Based Testing Strategy

| Property | Test approach |
|----------|--------------|
| FEFO always selects open pack before sealed | Generate random mix of open/sealed packs; assert first selected is open |
| FEFO tie-break uses lowest ID | Generate open packs with identical expiry; assert lowest ID selected first |
| Dispense cascade fills exact quantity | Vary pack sizes; assert sum of line item deductions == requested qty |
| Insufficient stock raises error, no mutation | Assert exception raised and all pack quantities unchanged |
| Write-off qty > remaining rejected | Assert 422 response; pack quantity unchanged |
| Invalid reason_code rejected | Assert 422 response |
| Countersign by initiator blocked | Assert 403 response |
| On-hand excludes expired packs | Generate packs with past expiry dates; assert not counted |
| Prediction forecast unchanged by write-offs | Insert write-offs; assert forecast output identical |

---

## Migration Strategy

1. New tables created on first `init_db()` call (SQLAlchemy `create_all`)
2. Existing `Batch` records are NOT migrated to `PackInstance` automatically — pack instances are created from new deliveries forward
3. `Sale` table is preserved unchanged — predictions continue to use it
4. `DispenseTransaction` records created from this point forward are also unioned into prediction demand signal
