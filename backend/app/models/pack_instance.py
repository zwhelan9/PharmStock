from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PackStatus(str, enum.Enum):
    SEALED = "sealed"
    OPEN = "open"
    EMPTY = "empty"


class PackInstance(Base):
    __tablename__ = "pack_instances"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)

    batch_number = Column(String(100), nullable=False)
    lot_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=False, index=True)

    quantity_received = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)

    unit_cost = Column(Float, nullable=True)
    status = Column(Enum(PackStatus), nullable=False, default=PackStatus.SEALED, index=True)
    date_opened = Column(Date, nullable=True)
    is_controlled_drug = Column(Boolean, default=False, nullable=False)

    supplier_invoice = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="pack_instances")
    batch = relationship("Batch", backref="pack_instances")
    dispense_line_items = relationship("DispenseLineItem", back_populates="pack_instance")
    write_offs = relationship("WriteOff", back_populates="pack_instance")
