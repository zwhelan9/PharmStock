from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ReconciliationAdjustment(Base):
    __tablename__ = "reconciliation_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)

    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)  # min 1 char enforced in schema

    adjusted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    touchstore_reported = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="reconciliation_adjustments")
    adjusted_by = relationship("User", backref="reconciliation_adjustments")
