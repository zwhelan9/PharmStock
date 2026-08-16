from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ChangeType(str, enum.Enum):
    STOCK_IN = "stock_in"           # New batch received
    SALE = "sale"                   # Dispensed to customer
    ADJUSTMENT = "adjustment"       # Manual correction (damage, count discrepancy)
    RETURN = "return"               # Returned to supplier
    EXPIRED = "expired"             # Written off as expired
    TRANSFER = "transfer"           # Moved between locations
    OPENING = "opening"             # Opening stock entry


class StockLog(Base):
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)

    change_type = Column(Enum(ChangeType), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)          # positive = added, negative = removed
    stock_before = Column(Integer, nullable=True)       # total stock before this change
    stock_after = Column(Integer, nullable=True)        # total stock after this change

    reference = Column(String(100), nullable=True)     # invoice no, sale ref, etc.
    performed_by = Column(String(100), nullable=True)  # staff member
    notes = Column(Text, nullable=True)

    log_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="stock_logs")
    batch = relationship("Batch", back_populates="stock_logs")
