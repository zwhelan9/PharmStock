from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    generic_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=False)          # e.g. Antibiotic, Analgesic, OTC
    subcategory = Column(String(100), nullable=True)
    manufacturer = Column(String(150), nullable=True)
    supplier = Column(String(150), nullable=True)
    unit = Column(String(50), nullable=False, default="Tablet")  # Tablet, Capsule, Bottle, Vial, Sachet
    unit_size = Column(String(50), nullable=True)                # e.g. "500mg", "100ml"
    barcode = Column(String(100), nullable=True, unique=True)
    description = Column(Text, nullable=True)

    # Pricing
    selling_price = Column(Float, nullable=True)

    # Reorder settings
    reorder_level = Column(Integer, nullable=False, default=50)   # trigger reorder when stock <= this
    reorder_quantity = Column(Integer, nullable=False, default=200)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    batches = relationship("Batch", back_populates="medicine", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="medicine", cascade="all, delete-orphan")
    stock_logs = relationship("StockLog", back_populates="medicine", cascade="all, delete-orphan")
    expiry_logs = relationship("ExpiryLog", back_populates="medicine", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="medicine", cascade="all, delete-orphan")
