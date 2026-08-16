from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class PredictionRead(BaseModel):
    id: int
    medicine_id: int
    forecast_date: date
    horizon_days: int
    predicted_quantity: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_score: Optional[float] = None
    model_used: Optional[str] = None
    generated_at: Optional[datetime] = None
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ForecastSummary(BaseModel):
    medicine_id: int
    medicine_name: str
    horizon_days: int
    total_predicted: float
    current_stock: int
    days_until_stockout: Optional[int] = None
    reorder_recommended: bool
    daily_breakdown: List[PredictionRead] = []
