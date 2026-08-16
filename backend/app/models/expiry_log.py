from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ExpiryAction(str, enum.Enum):
    REMOVED = "removed"           # Removed from shelf, disposed
    RETURNED = "returned"         # Returned to supplier before expiry
    DONATED = "donated"           # Donated (near-expiry)
    DESTROYED = "destroyed"       # Formally destroyed / incinerated
    QUARANTINED = "quarantined"   # Held pending decision


class ExpiryLog(Base):
    __tablename__ = "expiry_logs"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)

    expiry_date = Column(Date, nullable=False, index=True)
    quantity_affected = Column(Integer, nullable=False)
    quantity_wasted = Column(Integer, nullable=True)       # units that could not be salvaged
    estimated_loss = Column(Float, nullable=True)          # cost_price * quantity_wasted

    action = Column(Enum(ExpiryAction), nullable=False)
    action_date = Column(Date, nullable=False)

    performed_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="expiry_logs")
    batch = relationship("Batch", back_populates="expiry_logs")
