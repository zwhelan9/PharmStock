from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)

    batch_number = Column(String(100), nullable=False)
    supplier_invoice = Column(String(100), nullable=True)
    supplier = Column(String(150), nullable=True)

    # Quantities
    quantity_received = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)

    # Pricing
    cost_price = Column(Float, nullable=True)          # per unit cost

    # Dates
    purchase_date = Column(Date, nullable=False)
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False, index=True)

    # Status
    is_active = Column(Boolean, default=True)          # False when fully consumed or expired
    is_quarantined = Column(Boolean, default=False)    # Flagged for quality issues

    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="batches")
    sales = relationship("Sale", back_populates="batch")
    stock_logs = relationship("StockLog", back_populates="batch")
    expiry_logs = relationship("ExpiryLog", back_populates="batch")
