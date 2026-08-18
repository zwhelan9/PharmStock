from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ReasonCode(str, enum.Enum):
    DAMAGED = "damaged"
    EXPIRED = "expired"
    SPILLAGE_CONTAMINATION = "spillage_contamination"
    SHORT_DATED_RETURN_TO_SUPPLIER = "short_dated_return_to_supplier"
    DISPENSING_ERROR = "dispensing_error"
    THEFT_LOSS = "theft_loss"
    RECALL = "recall"


class WriteOffStatus(str, enum.Enum):
    PENDING_COUNTERSIGN = "pending_countersign"
    FINALISED = "finalised"


class WriteOff(Base):
    __tablename__ = "write_offs"

    id = Column(Integer, primary_key=True, index=True)
    pack_instance_id = Column(Integer, ForeignKey("pack_instances.id"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    reason_code = Column(Enum(ReasonCode), nullable=False)
    notes = Column(Text, nullable=True)  # max 500 chars enforced in schema

    calculated_value = Column(Float, nullable=True)
    cost_unavailable = Column(Boolean, nullable=False, default=False)

    status = Column(Enum(WriteOffStatus), nullable=False, default=WriteOffStatus.FINALISED)

    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    initiated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    countersigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    countersigned_at = Column(DateTime(timezone=True), nullable=True)
    countersign_deadline = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pack_instance = relationship("PackInstance", back_populates="write_offs")
    medicine = relationship("Medicine", backref="write_offs")
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id], backref="initiated_write_offs")
    countersigned_by = relationship("User", foreign_keys=[countersigned_by_user_id], backref="countersigned_write_offs")
