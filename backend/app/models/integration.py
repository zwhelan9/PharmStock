"""
Dispensing Integration Layer Models
=====================================
ImportLog: Audit trail for every import run (file or API)
StockSnapshot: Point-in-time stock levels from the source system
QuarantinedRecord: Rejected/malformed rows from imports
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ImportLog(Base):
    """Audit log of every import run — tracks source, timing, results."""
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # file_upload | api | scheduled
    source_filename = Column(String(255), nullable=True)
    import_type = Column(String(50), nullable=False)  # dispense_events | stock_snapshot | product_master
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="running")  # running | completed | failed
    total_records = Column(Integer, nullable=False, default=0)
    records_processed = Column(Integer, nullable=False, default=0)
    records_rejected = Column(Integer, nullable=False, default=0)
    records_deduplicated = Column(Integer, nullable=False, default=0)
    reconciliation_result = Column(String(50), nullable=True)  # match | discrepancy | not_checked
    error_message = Column(Text, nullable=True)
    imported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    imported_by = relationship("User", backref="import_logs")
    quarantined_records = relationship("QuarantinedRecord", back_populates="import_log", cascade="all, delete-orphan")


class StockSnapshot(Base):
    """Point-in-time stock level from the source dispensing system."""
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    quantity_on_hand = Column(Integer, nullable=False)
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False)
    import_log_id = Column(Integer, ForeignKey("import_logs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="stock_snapshots")
    import_log = relationship("ImportLog", backref="stock_snapshots")


class QuarantinedRecord(Base):
    """Rejected/malformed rows from an import — stored for review, never processed."""
    __tablename__ = "quarantined_records"

    id = Column(Integer, primary_key=True, index=True)
    import_log_id = Column(Integer, ForeignKey("import_logs.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=True)
    raw_data = Column(Text, nullable=False)  # Original row as JSON
    rejection_reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    import_log = relationship("ImportLog", back_populates="quarantined_records")


class DispenseEvent(Base):
    """Individual dispense event ingested from external system — deduplicated by event_id."""
    __tablename__ = "dispense_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(200), nullable=False, unique=True, index=True)  # Dedup key
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    quantity_dispensed = Column(Integer, nullable=False)
    pack_size = Column(Integer, nullable=True)
    batch_number = Column(String(100), nullable=True)
    is_controlled_drug = Column(Boolean, nullable=False, default=False)
    transaction_type = Column(String(20), nullable=False, default="dispense")  # dispense | return | adjustment | destruction
    import_log_id = Column(Integer, ForeignKey("import_logs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medicine = relationship("Medicine", backref="dispense_events")
    import_log = relationship("ImportLog", backref="dispense_events")
