from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)

    # Forecast window
    forecast_date = Column(Date, nullable=False, index=True)   # the date being predicted
    horizon_days = Column(Integer, nullable=False)             # 7, 14, or 30

    predicted_quantity = Column(Float, nullable=False)         # predicted units needed
    lower_bound = Column(Float, nullable=True)                 # confidence interval low
    upper_bound = Column(Float, nullable=True)                 # confidence interval high
    confidence_score = Column(Float, nullable=True)            # 0.0 – 1.0

    model_used = Column(String(100), nullable=True)            # e.g. "LinearRegression", "MovingAverage"
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    medicine = relationship("Medicine", back_populates="predictions")
