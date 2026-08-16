# Pharmacy Stock Prediction System

A full-stack web application for pharmacy inventory management with ML-powered demand forecasting, expiry date tracking, and automated reorder alerts.

---

## Features

- **Medicine Catalogue** — CRUD for all medicines with category, supplier, pricing
- **Batch & Stock Management** — Track every stock delivery with batch numbers, FEFO ordering
- **Expiry Tracking** — 4-tier alert system (expired / critical ≤30d / warning ≤60d / watch ≤90d), expiry calendar, waste loss estimation
- **Demand Forecasting** — ML model (Linear Regression + Moving Average) predicts 7/14/30-day demand per medicine with confidence intervals
- **Reorder Alerts** — Auto-generates reorder recommendations when predicted stockout is imminent
- **Sales History** — Record dispensing events, charts of daily/medicine sales trends
- **Dashboard** — KPI cards, active alert feed, sales charts

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Database | SQLite (via SQLAlchemy 2.0) |
| ML | scikit-learn, pandas, numpy |
| Frontend | React 18, Vite, Tailwind CSS |
| Charts | Recharts |
| HTTP | Axios |

---

## Project Structure

```
Pharmacy project/
├── backend/
│   ├── app/
│   │   ├── core/         # config.py, database.py
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── routers/      # FastAPI route handlers
│   │   ├── ml/           # forecaster.py
│   │   └── main.py       # FastAPI app entry point
│   ├── seed.py           # Database seed script
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/          # Axios service layer
    │   ├── components/   # Layout, Sidebar, StatCard, AlertBadge, etc.
    │   ├── pages/        # Dashboard, Medicines, StockManagement, ExpiryTracking, Predictions, SalesHistory
    │   ├── App.jsx
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

---

## Setup & Run

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Seed the database with sample data (20 medicines, 180 days of sales)
python seed.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

App available at: http://localhost:5173

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /api/v1/medicines/ | List all medicines |
| POST | /api/v1/medicines/ | Create medicine |
| GET | /api/v1/batches/ | List batches |
| POST | /api/v1/batches/ | Add new batch (triggers stock-in log) |
| GET | /api/v1/batches/medicine/{id}/fefo | FEFO-ordered batches for a medicine |
| POST | /api/v1/sales/ | Record a sale (auto FEFO batch selection) |
| GET | /api/v1/sales/summary/daily | Daily sales totals |
| GET | /api/v1/stock/summary | Dashboard KPIs |
| GET | /api/v1/stock/levels | Current stock per medicine |
| GET | /api/v1/expiry/alerts | Tiered expiry alerts |
| GET | /api/v1/expiry/calendar | Expiry calendar by month |
| POST | /api/v1/expiry/logs | Log expired batch removal |
| GET | /api/v1/predictions/forecast/{id} | Run ML forecast for a medicine |
| GET | /api/v1/predictions/reorder-list | All medicines needing reorder |
| GET | /api/v1/alerts/ | Consolidated alert feed |

---

## ML Forecasting Logic

The forecaster selects a model based on available history:

| History Available | Model Used |
|---|---|
| < 7 days | Global Average (flat fallback) |
| 7–29 days | Weighted Moving Average + linear trend |
| 30+ days | Linear Regression (trend + day-of-week features) |

Outputs include per-day predicted quantity, lower/upper confidence bounds, confidence score, and model name.
