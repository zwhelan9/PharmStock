from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone

from app.core.database import get_db
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.models.sale import Sale
from app.models.prediction import Prediction
from app.models.pack_instance import PackInstance, PackStatus
from app.models.dispense_transaction import DispenseTransaction
from app.schemas.prediction import PredictionRead, ForecastSummary
from app.ml.forecaster import generate_forecast, days_until_stockout
from app.core.config import settings

router = APIRouter(prefix="/predictions", tags=["Predictions"])

# Cache freshness: reuse DB predictions younger than this
CACHE_TTL_MINUTES = 60


def _get_sales_history(medicine_id: int, db: Session) -> list:
    """
    Demand signal = historical Sale records UNION DispenseTransaction records.
    Write-offs are excluded (they are a separate model entirely).
    """
    # Legacy sales
    sale_rows = (
        db.query(Sale.sale_date, Sale.quantity)
        .filter(Sale.medicine_id == medicine_id)
        .all()
    )
    records = [
        {"sale_date": r.sale_date.date() if hasattr(r.sale_date, "date") else r.sale_date, "quantity": r.quantity}
        for r in sale_rows
    ]

    # New dispense transactions (post pack-tracking)
    dispense_rows = (
        db.query(DispenseTransaction.dispense_date, DispenseTransaction.total_quantity)
        .filter(DispenseTransaction.medicine_id == medicine_id)
        .all()
    )
    for r in dispense_rows:
        d = r.dispense_date.date() if hasattr(r.dispense_date, "date") else r.dispense_date
        records.append({"sale_date": d, "quantity": r.total_quantity})

    return records


def _current_stock(medicine_id: int, db: Session) -> int:
    """
    On-hand quantity: prefer PackInstance sum (sealed/open, non-expired).
    Falls back to Batch.quantity_remaining if no pack instances exist yet
    (backward compatibility for medicines not yet tracked at pack level).
    """
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

    # Fallback: legacy Batch-level tracking
    return (
        db.query(func.sum(Batch.quantity_remaining))
        .filter(Batch.medicine_id == medicine_id, Batch.is_active == True)
        .scalar() or 0
    )


def _cached_summary(medicine: Medicine, horizon: int, db: Session) -> Optional[ForecastSummary]:
    """Return a ForecastSummary built from cached DB predictions if they are fresh enough."""
    cutoff_time = datetime.now() - timedelta(minutes=CACHE_TTL_MINUTES)
    today = date.today()

    rows = (
        db.query(Prediction)
        .filter(
            Prediction.medicine_id == medicine.id,
            Prediction.horizon_days == horizon,
            Prediction.forecast_date > today,
            Prediction.generated_at >= cutoff_time,
        )
        .order_by(Prediction.forecast_date.asc())
        .all()
    )

    if len(rows) < horizon:
        return None  # stale or missing — needs recompute

    stock = _current_stock(medicine.id, db)
    total_predicted = sum(r.predicted_quantity for r in rows)

    # Reconstruct stockout day from cached data
    remaining = float(stock)
    stockout_day = None
    for i, r in enumerate(rows):
        remaining -= r.predicted_quantity
        if remaining <= 0:
            stockout_day = i + 1
            break

    daily = [
        PredictionRead(
            id=r.id,
            medicine_id=r.medicine_id,
            forecast_date=r.forecast_date,
            horizon_days=r.horizon_days,
            predicted_quantity=r.predicted_quantity,
            lower_bound=r.lower_bound,
            upper_bound=r.upper_bound,
            confidence_score=r.confidence_score,
            model_used=r.model_used,
            generated_at=r.generated_at,
            medicine_name=medicine.name,
        )
        for r in rows
    ]

    return ForecastSummary(
        medicine_id=medicine.id,
        medicine_name=medicine.name,
        horizon_days=horizon,
        total_predicted=round(total_predicted, 2),
        current_stock=stock,
        days_until_stockout=stockout_day,
        reorder_recommended=(
            stockout_day is not None and stockout_day <= horizon
        ) or (stock <= medicine.reorder_level),
        daily_breakdown=daily,
    )


def _run_forecast(medicine_id: int, horizon: int, db: Session) -> ForecastSummary:
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # Serve from cache if fresh
    cached = _cached_summary(medicine, horizon, db)
    if cached:
        return cached

    sales = _get_sales_history(medicine_id, db)
    forecast = generate_forecast(medicine_id, sales, horizon_days=horizon)
    stock = _current_stock(medicine_id, db)
    stockout_day = days_until_stockout(stock, forecast)

    # Persist predictions (replace existing for same medicine + horizon + future dates)
    today = date.today()
    db.query(Prediction).filter(
        Prediction.medicine_id == medicine_id,
        Prediction.horizon_days == horizon,
        Prediction.forecast_date > today,
    ).delete()

    for f in forecast.forecasts:
        p = Prediction(
            medicine_id=medicine_id,
            forecast_date=f.forecast_date,
            horizon_days=horizon,
            predicted_quantity=f.predicted_quantity,
            lower_bound=f.lower_bound,
            upper_bound=f.upper_bound,
            confidence_score=f.confidence_score,
            model_used=f.model_used,
        )
        db.add(p)

    db.commit()

    daily = [
        PredictionRead(
            id=0,
            medicine_id=medicine_id,
            forecast_date=f.forecast_date,
            horizon_days=horizon,
            predicted_quantity=f.predicted_quantity,
            lower_bound=f.lower_bound,
            upper_bound=f.upper_bound,
            confidence_score=f.confidence_score,
            model_used=f.model_used,
            medicine_name=medicine.name,
        )
        for f in forecast.forecasts
    ]

    return ForecastSummary(
        medicine_id=medicine_id,
        medicine_name=medicine.name,
        horizon_days=horizon,
        total_predicted=forecast.total_predicted,
        current_stock=stock,
        days_until_stockout=stockout_day,
        reorder_recommended=(
            stockout_day is not None and stockout_day <= horizon
        ) or (stock <= medicine.reorder_level),
        daily_breakdown=daily,
    )


@router.get("/forecast/{medicine_id}", response_model=ForecastSummary)
def forecast_medicine(
    medicine_id: int,
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Run a demand forecast for a single medicine."""
    if horizon not in settings.FORECAST_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {settings.FORECAST_HORIZONS}")
    return _run_forecast(medicine_id, horizon, db)


@router.get("/forecast/all/summary")
def forecast_all(
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Run forecasts for all medicines and return reorder recommendations."""
    if horizon not in settings.FORECAST_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {settings.FORECAST_HORIZONS}")

    medicines = db.query(Medicine).all()
    results = []
    for m in medicines:
        try:
            summary = _run_forecast(m.id, horizon, db)
            results.append({
                "medicine_id": summary.medicine_id,
                "medicine_name": summary.medicine_name,
                "current_stock": summary.current_stock,
                "total_predicted": summary.total_predicted,
                "days_until_stockout": summary.days_until_stockout,
                "reorder_recommended": summary.reorder_recommended,
            })
        except Exception:
            continue
    return results


@router.get("/reorder-list")
def reorder_list(
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Returns only medicines that need reordering."""
    all_summaries = forecast_all(horizon=horizon, db=db)
    return [s for s in all_summaries if s["reorder_recommended"]]


@router.get("/history/{medicine_id}", response_model=List[PredictionRead])
def prediction_history(
    medicine_id: int,
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Prediction)
        .filter(Prediction.medicine_id == medicine_id, Prediction.horizon_days == horizon)
        .order_by(Prediction.forecast_date.asc())
        .all()
    )
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    return [
        PredictionRead(
            id=r.id,
            medicine_id=r.medicine_id,
            forecast_date=r.forecast_date,
            horizon_days=r.horizon_days,
            predicted_quantity=r.predicted_quantity,
            lower_bound=r.lower_bound,
            upper_bound=r.upper_bound,
            confidence_score=r.confidence_score,
            model_used=r.model_used,
            generated_at=r.generated_at,
            medicine_name=medicine.name if medicine else None,
        )
        for r in rows
    ]



def _get_sales_history(medicine_id: int, db: Session) -> list:
    rows = (
        db.query(Sale.sale_date, Sale.quantity)
        .filter(Sale.medicine_id == medicine_id)
        .all()
    )
    return [{"sale_date": r.sale_date.date() if hasattr(r.sale_date, "date") else r.sale_date, "quantity": r.quantity} for r in rows]


def _current_stock(medicine_id: int, db: Session) -> int:
    return (
        db.query(func.sum(Batch.quantity_remaining))
        .filter(Batch.medicine_id == medicine_id, Batch.is_active == True)
        .scalar() or 0
    )


def _run_forecast(medicine_id: int, horizon: int, db: Session) -> ForecastSummary:
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    sales = _get_sales_history(medicine_id, db)
    forecast = generate_forecast(medicine_id, sales, horizon_days=horizon)
    stock = _current_stock(medicine_id, db)
    stockout_day = days_until_stockout(stock, forecast)

    # Persist predictions (replace existing for same medicine + horizon + future dates)
    today = date.today()
    db.query(Prediction).filter(
        Prediction.medicine_id == medicine_id,
        Prediction.horizon_days == horizon,
        Prediction.forecast_date > today,
    ).delete()

    pred_rows = []
    for f in forecast.forecasts:
        p = Prediction(
            medicine_id=medicine_id,
            forecast_date=f.forecast_date,
            horizon_days=horizon,
            predicted_quantity=f.predicted_quantity,
            lower_bound=f.lower_bound,
            upper_bound=f.upper_bound,
            confidence_score=f.confidence_score,
            model_used=f.model_used,
        )
        db.add(p)
        pred_rows.append(p)

    db.commit()

    daily = [
        PredictionRead(
            id=0,
            medicine_id=medicine_id,
            forecast_date=f.forecast_date,
            horizon_days=horizon,
            predicted_quantity=f.predicted_quantity,
            lower_bound=f.lower_bound,
            upper_bound=f.upper_bound,
            confidence_score=f.confidence_score,
            model_used=f.model_used,
            medicine_name=medicine.name,
        )
        for f in forecast.forecasts
    ]

    return ForecastSummary(
        medicine_id=medicine_id,
        medicine_name=medicine.name,
        horizon_days=horizon,
        total_predicted=forecast.total_predicted,
        current_stock=stock,
        days_until_stockout=stockout_day,
        reorder_recommended=(
            stockout_day is not None and stockout_day <= horizon
        ) or (stock <= medicine.reorder_level),
        daily_breakdown=daily,
    )


@router.get("/forecast/{medicine_id}", response_model=ForecastSummary)
def forecast_medicine(
    medicine_id: int,
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Run a demand forecast for a single medicine."""
    if horizon not in settings.FORECAST_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {settings.FORECAST_HORIZONS}")
    return _run_forecast(medicine_id, horizon, db)


@router.get("/forecast/all/summary")
def forecast_all(
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Run forecasts for all medicines and return reorder recommendations."""
    if horizon not in settings.FORECAST_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {settings.FORECAST_HORIZONS}")

    medicines = db.query(Medicine).all()
    results = []
    for m in medicines:
        try:
            summary = _run_forecast(m.id, horizon, db)
            results.append({
                "medicine_id": summary.medicine_id,
                "medicine_name": summary.medicine_name,
                "current_stock": summary.current_stock,
                "total_predicted": summary.total_predicted,
                "days_until_stockout": summary.days_until_stockout,
                "reorder_recommended": summary.reorder_recommended,
            })
        except Exception:
            continue
    return results


@router.get("/reorder-list")
def reorder_list(
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Returns only medicines that need reordering."""
    all_summaries = forecast_all(horizon=horizon, db=db)
    return [s for s in all_summaries if s["reorder_recommended"]]


@router.get("/history/{medicine_id}", response_model=List[PredictionRead])
def prediction_history(
    medicine_id: int,
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Prediction)
        .filter(Prediction.medicine_id == medicine_id, Prediction.horizon_days == horizon)
        .order_by(Prediction.forecast_date.asc())
        .all()
    )
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    return [
        PredictionRead(
            id=r.id,
            medicine_id=r.medicine_id,
            forecast_date=r.forecast_date,
            horizon_days=r.horizon_days,
            predicted_quantity=r.predicted_quantity,
            lower_bound=r.lower_bound,
            upper_bound=r.upper_bound,
            confidence_score=r.confidence_score,
            model_used=r.model_used,
            generated_at=r.generated_at,
            medicine_name=medicine.name if medicine else None,
        )
        for r in rows
    ]
