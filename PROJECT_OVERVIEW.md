# PharmStock — AI Pharmacy Stock Prediction System

*A decision-support platform that helps pharmacies stop guessing about stock.*

---

## 1. The Elevator Pitch (30 seconds)

> Pharmacies lose money two ways: running out of medicine patients need, and letting stock expire on the shelf. Most still reorder on gut feeling. PharmStock reads a pharmacy's own sales history, current stock, and seasonal patterns, then tells the pharmacist exactly what to reorder and when — with the numbers to back it up. It also handles the strict legal side: controlled-drug registers, expiry tracking, and stock write-offs, all in one place.

**One-line version:** *"It's the difference between 'I think we're low on amoxicillin' and 'we'll sell 47 units next week, we have 18, order 35.'"*

---

## 2. The Problem (why anyone should care)

Pharmacies typically reorder based on gut feeling, fixed par levels, or reacting to empty shelves. That causes:

- **Lost sales & patient care gaps** when critical medications run out
- **Cash tied up** in excess inventory sitting on shelves
- **Expired stock** written off as pure loss
- **Wasted staff hours** manually reviewing stock sheets

For controlled drugs there's an added layer: strict legal record-keeping (in Ireland, PSI/HPRA rules) where mistakes carry real regulatory risk.

---

## 3. The Solution (what it does)

PharmStock turns raw pharmacy data into actions:

```
Sales history + current stock + seasonal trends
          ↓
   AI prediction engine
          ↓
Reorder recommendations + risk alerts + compliance records
          ↓
   A dashboard a pharmacist acts on
```

The key design principle: **the system recommends, humans decide.** It never auto-orders or auto-dispenses — it's an analytics layer on top of the pharmacy's existing systems, not a replacement for them.

---

## 4. Core Features (the demo walkthrough)

Walk an interviewer through these in order — it tells a story.

### Dashboard
The landing page. Real-time stock value, stockout risk count, expiry risk count, demand charts, and top movers. *"This is what the pharmacist sees first thing in the morning."*

### Medicines & Inventory
The product catalogue plus a unified inventory view. Inventory tracks stock two ways:
- **Aggregate stock levels & batches** (the traditional view)
- **Pack-level tracking** — every physical pack tracked individually as *Sealed → Open → Empty*, so the system knows exactly how many loose units are in an opened box.

### Forecasting & Reorder
The heart of the product:
- **Demand forecasts** per medicine for 7 / 14 / 30 days, with a confidence range
- **Reorder recommendations**: `predicted demand + safety stock − current stock`, rounded to pack sizes, grouped by supplier, one-click CSV export
- **Dead stock detection** (no sales in X days = cash frozen on the shelf)
- **Demand anomaly detection** (sudden spikes or drops worth a human look)

### FEFO Dispensing
When stock is dispensed, the system automatically draws from the **First-Expired-First-Out** pack — opened packs before sealed ones, earliest expiry first. This is how real pharmacies are *supposed* to work; the software enforces it.

### Write-Offs
Formal recording of damaged / expired / lost stock, with reason codes. Crucially, write-offs are kept **separate from sales** so they never pollute the demand forecast — a loss is not demand.

### Expiry Tracking
Batch-level and pack-level expiry alerts, tiered (Critical / Warning / Watch), with the estimated financial value at risk.

### Controlled Drugs Module
The compliance showpiece, aligned to the Misuse of Drugs Regulations 2026 (S.I. 139/2026):
- **Append-only CD register** — entries can never be silently edited or deleted; corrections create a new linked record, preserving the original
- **Automatic running balance** (never manually typed)
- **Duty register** of pharmacists on duty
- **Destruction records** requiring a second witness to re-authenticate with their password, producing a tamper-evident digital signature
- **CD anomaly detection** — flags unusual dispensing patterns for pharmacist review

### Data Import & Reconciliation
A read-only integration layer that ingests dispensing data from external systems (e.g. TouchStore Rx) via CSV, API, or manual upload. It validates every row, deduplicates, quarantines bad data, and reconciles the system's stock figure against the source — flagging discrepancies rather than silently trusting either number.

---

## 5. What Makes It Interview-Worthy (the engineering story)

These are the talking points that show depth, not just "I built a CRUD app."

### Append-only audit trail
The CD register is legally required to be tamper-evident. Instead of updating rows, a correction **voids** the original (keeping it visible) and writes a new linked entry. This is the same pattern banks use for ledgers — event sourcing thinking applied to a regulatory requirement.

### Separation of signals
Sales, dispenses, and write-offs are deliberately kept as distinct record types. This matters because the forecast must only learn from *actual patient demand* — a write-off (loss) or a stock correction is not demand. Mixing them would quietly corrupt every prediction.

### FEFO as a pure service
The dispensing algorithm is a standalone service that, given a medicine and quantity, returns which packs to draw from — without touching the database. That makes it independently testable and means the same logic serves both manual dispensing and imported dispensing events.

### Read-only integration boundary
The integration layer *consumes* events and *produces* recommendations but never writes back to the dispensing system. This keeps the product firmly in "analytics tool" territory rather than "second dispensing record," which is a deliberate scope and liability decision.

### Idempotent ingestion
Re-importing the same file twice can't double-count, because every dispense event is deduplicated by a unique `event_id`. Malformed rows are quarantined with a reason, never silently dropped — so the data feeding the forecast is trustworthy.

### Graceful degradation
The prediction engine caches results and falls back to a category average for products with too little history. Stock calculations fall back from pack-level to batch-level tracking when packs aren't set up yet. Nothing hard-fails on missing data.

---

## 6. Technical Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Frontend    │────▶│  REST API     │────▶│  Services & Models   │
│  React + Vite│     │  FastAPI      │     │  FEFO, Forecasting,  │
│  Tailwind    │◀────│  JWT auth     │◀────│  Write-off, CD, etc. │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                                                      │
                                              ┌───────▼───────┐
                                              │  SQLite (SQLAlchemy) │
                                              └───────────────┘
```

### Stack
| Layer | Technology | Why |
|---|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts | Fast dev loop, responsive, works on an in-store tablet |
| Routing | React Router 6 | Clean multi-page SPA |
| Backend | FastAPI (Python 3.13) | Auto-generated API docs, type-safe request validation |
| ORM / DB | SQLAlchemy 2.0 + SQLite | Zero-config for a demo; swappable to PostgreSQL for production |
| Auth | JWT (python-jose) + bcrypt (passlib) | Role-based access: admin / staff / viewer |
| Validation | Pydantic v2 | Every API payload is schema-checked |

### Why these choices (for the interview)
- **FastAPI** gives interactive API docs for free at `/docs` — great for a demo, and its Pydantic integration means validation errors are caught at the edge, not deep in business logic.
- **SQLite** keeps the demo one-command-to-run, but because everything goes through SQLAlchemy, moving to PostgreSQL for a multi-store deployment is a config change, not a rewrite.
- **Service layer** (FEFO, write-off, CD, ingestion) is kept separate from the API routers, so business logic is testable in isolation and reusable across endpoints.

### Project structure
```
backend/
  app/
    core/        → config, database, security (JWT/hashing)
    models/      → SQLAlchemy tables
    schemas/     → Pydantic request/response contracts
    routers/     → API endpoints, grouped by feature
    services/    → business logic (FEFO, write-off, CD register, ingestion)
frontend/
  src/
    api/         → typed API client wrappers
    components/  → shared UI (Sidebar, Topbar, badges, spinners)
    pages/       → one file per screen
    context/     → auth state
```

---

## 7. Security & Compliance (a serious differentiator)

- **Role-based access control** — every route requires a valid token; sensitive actions (CD destruction) require re-authentication
- **Passwords** hashed with bcrypt, never stored in plaintext
- **Audit logging** — every stock-affecting action records who did it and when
- **Append-only registers** for controlled drugs — tamper-evident by design
- **Read-only external boundary** — the system never writes to the dispensing system, limiting blast radius and the sensitive data it touches
- **Narrow data contract** — deliberately does *not* ingest patient names, diagnoses, or payment detail beyond what's legally required

---

## 8. Measurable Value (the business case)

Frame the pitch around outcomes, not features:

| Goal | Target |
|---|---|
| Reduce stockouts | ↓ 50% of SKUs out of stock, within 6 months |
| Reduce expiry waste | ↓ 30% value of written-off stock |
| Improve cash efficiency | ↑ 20% inventory turnover |
| Save staff time | ↓ 70% hours/week on manual stock review |
| Forecast accuracy | < 20% error (MAPE) on top-volume products |

---

## 9. Scope & Honesty (what it doesn't do — v1)

Being upfront about scope is a strength in an interview:

- No **auto-ordering** — the system recommends, a human approves. Deliberate, for safety and liability.
- **Single jurisdiction** (Ireland/PSI rules) — not multi-country regulatory compliance yet.
- Not a **certified compliance product** — built *toward* the 2026 electronic record-keeping standard, which itself has no formal software verification process published yet.
- Forecasting is **product-level**, not patient/prescription-level.
- The dispensing-system integration currently runs on **CSV import**; a live vendor API is the aspirational next tier.

---

## 10. Roadmap (where it goes next)

- **Live API integration** with TouchStore Rx / MPS once a data-sharing agreement exists
- **Multi-store** support (the schema already anticipates a `location_id`)
- **Stronger ML models** (gradient-boosted forecasting with engineered seasonal features) once data volume justifies it over the statistical baseline
- **Email / push notifications** for critical stockout and expiry alerts
- **Automated model retraining** with performance monitoring and drift alerts

---

## 11. Demo Script (5 minutes, for an interview or sales call)

1. **Log in** — show the role-based login (admin / staff / viewer). *"Not everyone can touch the controlled-drug register."*
2. **Dashboard** — *"Morning glance: what's at risk, what's it worth."*
3. **Forecasting & Reorder** — pick a medicine, show the forecast chart and confidence band, then the reorder table. *"Here's the pitch in one screen: predicted demand, current stock, recommended order. Export to CSV, hand it to the supplier."*
4. **Inventory → Packs** — show the Sealed / Open / Empty tracking. *"This is why the numbers are accurate — we track the loose units in an opened box, not just whole packs."*
5. **Dispense** — dispense a few units, show FEFO pick the right pack automatically.
6. **Controlled Drugs** — create a register entry, then *correct* it. *"Watch — the original doesn't disappear. It's legally required to be tamper-evident, and it is."* Then show a destruction record needing a witness password.
7. **Data Import** — upload a messy CSV with a couple of bad rows. *"It quarantines the bad data and reconciles the rest against what we think is on the shelf — flagging anything that doesn't match."*

**Closing line:** *"Everything you saw runs on the pharmacy's own data, respects the human in the loop, and keeps a clean audit trail — which is exactly what a regulated business needs before it trusts software with its stock."*

---

## 12. Anticipated Interview Questions

**"Why not just use spreadsheets?"**
Spreadsheets don't forecast, don't enforce FEFO, don't keep a tamper-evident audit trail, and don't reconcile against a dispensing system. And they break the moment two people edit them.

**"How accurate is the forecast?"**
The baseline uses the product's own sales history with seasonal and trend adjustment, targeting under 20% error on high-volume products. Low-history products fall back to a category average. The architecture supports swapping in stronger ML models as data grows — the forecasting engine is isolated behind a clean interface.

**"What happens if the data is wrong?"**
That's the reconciliation layer's whole job — it validates every import, quarantines bad rows, and flags discrepancies between its stock figure and the source system rather than blindly trusting either.

**"Is this safe for controlled drugs?"**
The CD register is append-only and tamper-evident, destruction needs a second witness to re-authenticate, and every action is attributed to an individual user. It's built to the 2026 regulations, though I'm careful to call it "built toward the standard" rather than certified — the formal verification process isn't published yet.

**"Why SQLite?"**
Zero-config for the demo. Everything runs through SQLAlchemy, so production is a connection-string change to PostgreSQL, not a rewrite. I chose to optimise for "runs in one command" at this stage.
