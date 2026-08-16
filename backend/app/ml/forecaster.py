"""
Demand Forecasting Module  — stdlib only (no numpy / sklearn / pandas)
=======================================================================
Predicts daily demand per medicine using historical sales data.

Strategy (tiered by data availability):
  < 7 days of history   -> GlobalAverage  (flat mean fallback)
  7-29 days             -> WeightedMovingAverage (exponential weights + trend)
  30+ days              -> LinearRegression (manual, trend + day-of-week bias)

All maths uses only Python's built-in math / statistics modules.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DailyForecast:
    def __init__(
        self,
        forecast_date: date,
        predicted_quantity: float,
        lower_bound: float,
        upper_bound: float,
        confidence_score: float,
        model_used: str,
    ):
        self.forecast_date      = forecast_date
        self.predicted_quantity = max(0.0, round(predicted_quantity, 2))
        self.lower_bound        = max(0.0, round(lower_bound, 2))
        self.upper_bound        = max(0.0, round(upper_bound, 2))
        self.confidence_score   = round(min(1.0, max(0.0, confidence_score)), 3)
        self.model_used         = model_used


class ForecastResult:
    def __init__(self, medicine_id: int, horizon_days: int, forecasts: List[DailyForecast]):
        self.medicine_id  = medicine_id
        self.horizon_days = horizon_days
        self.forecasts    = forecasts

    @property
    def total_predicted(self) -> float:
        return round(sum(f.predicted_quantity for f in self.forecasts), 2)


# ---------------------------------------------------------------------------
# Build a gap-filled daily series {date: qty}
# ---------------------------------------------------------------------------

def _build_daily(
    sales_records: List[Dict],
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
) -> List[float]:
    """
    Returns a list of daily totals (oldest first, gaps filled with 0).
    sales_records: [{'sale_date': date, 'quantity': int}, ...]
    """
    if not sales_records:
        return []

    agg: Dict[date, float] = defaultdict(float)
    for r in sales_records:
        d = r["sale_date"]
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        agg[d] += r["quantity"]

    if min_date is None:
        min_date = min(agg)
    if max_date is None:
        max_date = max(agg)

    series = []
    cur = min_date
    while cur <= max_date:
        series.append(agg.get(cur, 0.0))
        cur += timedelta(days=1)
    return series


# ---------------------------------------------------------------------------
# Simple linear regression (returns slope, intercept)
# ---------------------------------------------------------------------------

def _linreg(x: List[float], y: List[float]):
    n = len(x)
    if n < 2:
        return 0.0, (y[0] if y else 0.0)
    sx  = sum(x)
    sy  = sum(y)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    sx2 = sum(xi * xi for xi in x)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope     = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


# ---------------------------------------------------------------------------
# Model 1: Global Average
# ---------------------------------------------------------------------------

def _global_average(
    series: List[float],
    start_date: date,
    horizon: int,
    fallback: float = 2.0,
) -> List[DailyForecast]:
    avg = (sum(series) / len(series)) if series else fallback
    avg = max(avg, 0.0)
    std = _std(series) if len(series) > 1 else avg * 0.3

    return [
        DailyForecast(
            forecast_date      = start_date + timedelta(days=i),
            predicted_quantity = avg,
            lower_bound        = max(0.0, avg - std),
            upper_bound        = avg + std,
            confidence_score   = 0.50,
            model_used         = "GlobalAverage",
        )
        for i in range(horizon)
    ]


# ---------------------------------------------------------------------------
# Model 2: Weighted Moving Average + linear trend
# ---------------------------------------------------------------------------

def _weighted_moving_average(
    series: List[float],
    start_date: date,
    horizon: int,
    window: int = 7,
) -> List[DailyForecast]:
    n = len(series)
    w = min(window, n)

    # Exponential weights for the last `w` values
    raw_weights = [math.exp(k / w) for k in range(w)]
    total_w = sum(raw_weights)
    weights = [ww / total_w for ww in raw_weights]

    base = sum(series[n - w + k] * weights[k] for k in range(w))

    # Linear trend over full series
    xs = list(range(n))
    slope, _ = _linreg(xs, series)

    std = _std(series)

    return [
        DailyForecast(
            forecast_date      = start_date + timedelta(days=i),
            predicted_quantity = max(0.0, base + slope * (i + 1)),
            lower_bound        = max(0.0, base + slope * (i + 1) - 1.5 * std),
            upper_bound        = max(0.0, base + slope * (i + 1) + 1.5 * std),
            confidence_score   = 0.65,
            model_used         = "WeightedMovingAverage",
        )
        for i in range(horizon)
    ]


# ---------------------------------------------------------------------------
# Model 3: Linear Regression with day-of-week bias
# ---------------------------------------------------------------------------

def _linear_regression(
    series: List[float],
    start_date: date,
    as_of: date,
    horizon: int,
) -> List[DailyForecast]:
    n = len(series)

    # Compute day-of-week mean bias (0=Mon … 6=Sun)
    dow_totals: Dict[int, List[float]] = defaultdict(list)
    # series[0] corresponds to (as_of - n + 1) days ago
    series_start = as_of - timedelta(days=n - 1)
    for i, val in enumerate(series):
        d = series_start + timedelta(days=i)
        dow_totals[d.weekday()].append(val)

    global_mean = sum(series) / n if n else 1.0
    dow_bias: Dict[int, float] = {}
    for dow, vals in dow_totals.items():
        dow_mean = sum(vals) / len(vals)
        dow_bias[dow] = dow_mean / global_mean if global_mean > 0 else 1.0

    # Deseasonalise
    deseason = []
    for i, val in enumerate(series):
        d = series_start + timedelta(days=i)
        bias = dow_bias.get(d.weekday(), 1.0)
        deseason.append(val / bias if bias > 0 else val)

    # Fit trend on deseasonalised series
    xs = list(range(n))
    slope, intercept = _linreg(xs, deseason)

    # Residuals for confidence intervals
    residuals = [deseason[i] - (intercept + slope * i) for i in range(n)]
    res_std = _std(residuals)

    # R² as rough confidence proxy
    mean_ds = sum(deseason) / n
    ss_tot = sum((v - mean_ds) ** 2 for v in deseason)
    ss_res = sum(r ** 2 for r in residuals)
    r2 = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    confidence = max(0.55, min(0.95, r2))

    results = []
    for i in range(horizon):
        fdate = start_date + timedelta(days=i)
        trend_val = intercept + slope * (n + i)
        bias = dow_bias.get(fdate.weekday(), 1.0)
        pred = trend_val * bias

        results.append(DailyForecast(
            forecast_date      = fdate,
            predicted_quantity = max(0.0, pred),
            lower_bound        = max(0.0, pred - 1.96 * res_std * bias),
            upper_bound        = max(0.0, pred + 1.96 * res_std * bias),
            confidence_score   = confidence,
            model_used         = "LinearRegression",
        ))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_forecast(
    medicine_id: int,
    sales_records: List[Dict],
    horizon_days: int = 30,
    as_of: Optional[date] = None,
) -> ForecastResult:
    """
    Parameters
    ----------
    medicine_id   : DB id of the medicine
    sales_records : [{'sale_date': date|str, 'quantity': int}, ...]
    horizon_days  : 7, 14, or 30
    as_of         : treat as "today"; defaults to date.today()
    """
    if as_of is None:
        as_of = date.today()

    start_date = as_of + timedelta(days=1)

    # Limit to last 180 days
    cutoff = as_of - timedelta(days=180)
    recent = [r for r in sales_records if _to_date(r["sale_date"]) >= cutoff]

    series = _build_daily(recent, min_date=cutoff, max_date=as_of)
    n = len(series)

    if n < 7:
        forecasts = _global_average(series, start_date, horizon_days)
    elif n < 30:
        forecasts = _weighted_moving_average(series, start_date, horizon_days)
    else:
        try:
            forecasts = _linear_regression(series, start_date, as_of, horizon_days)
        except Exception:
            forecasts = _weighted_moving_average(series, start_date, horizon_days)

    return ForecastResult(
        medicine_id  = medicine_id,
        horizon_days = horizon_days,
        forecasts    = forecasts,
    )


def days_until_stockout(current_stock: int, forecast: ForecastResult) -> Optional[int]:
    """Returns the day index (1-based) when stock hits zero, or None if sufficient."""
    stock = float(current_stock)
    for i, f in enumerate(forecast.forecasts):
        stock -= f.predicted_quantity
        if stock <= 0:
            return i + 1
    return None


def _to_date(val) -> date:
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])
