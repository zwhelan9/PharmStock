from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DispenseSource(str, enum.Enum):
    MANUAL = "manual"
    TOUCHSTORE_RX = "touchstore_rx"


class DispenseTransaction(Base):
    __tablename__ = "dispense_transactions"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)

    total_quantity = Column(Integer, nullable=False)
    source = Column(Enum(DispenseSource), nullable=False, default=DispenseSource.MANUAL)
    touchstore_ref = Column(String(100), nullable=True)
    prescription_ref = Column(String(100), nullable=True)
    served_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    notes = Column(Text, nullable=True)
    dispense_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="dispense_transactions")
    served_by = relationship("User", backref="dispense_transactions")
    line_items = relationship("DispenseLineItem", back_populates="dispense_transaction", cascade="all, delete-orphan")


class DispenseLineItem(Base):
    __tablename__ = "dispense_line_items"

    id = Column(Integer, primary_key=True, index=True)
    dispense_transaction_id = Column(Integer, ForeignKey("dispense_transactions.id"), nullable=False, index=True)
    pack_instance_id = Column(Integer, ForeignKey("pack_instances.id"), nullable=False)

    quantity_deducted = Column(Integer, nullable=False)
    pack_status_after = Column(Enum("open", "empty", name="line_item_status"), nullable=False)

    # Relationships
    dispense_transaction = relationship("DispenseTransaction", back_populates="line_items")
    pack_instance = relationship("PackInstance", back_populates="dispense_line_items")
