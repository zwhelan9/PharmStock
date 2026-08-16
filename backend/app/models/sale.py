from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)

    # Customer info (optional / anonymised)
    customer_ref = Column(String(100), nullable=True)
    prescription_ref = Column(String(100), nullable=True)
    is_prescription = Column(Boolean, default=False)

    served_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    sale_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="sales")
    batch = relationship("Batch", back_populates="sales")
