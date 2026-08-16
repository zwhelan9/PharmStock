from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MedicineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    generic_name: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    unit: str = Field(default="Tablet", max_length=50)
    unit_size: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    selling_price: Optional[float] = Field(None, ge=0)
    reorder_level: int = Field(default=50, ge=0)
    reorder_quantity: int = Field(default=200, ge=1)


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    name: Optional[str] = None
    generic_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    unit: Optional[str] = None
    unit_size: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    selling_price: Optional[float] = None
    reorder_level: Optional[int] = None
    reorder_quantity: Optional[int] = None


class MedicineRead(MedicineBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Computed / aggregated fields (populated by router)
    total_stock: Optional[int] = None
    is_low_stock: Optional[bool] = None
    expiring_soon_count: Optional[int] = None   # batches expiring within 90 days

    model_config = {"from_attributes": True}


class MedicineListItem(BaseModel):
    id: int
    name: str
    category: str
    unit: str
    selling_price: Optional[float] = None
    reorder_level: int
    total_stock: Optional[int] = None
    is_low_stock: Optional[bool] = None
    expiring_soon_count: Optional[int] = None

    model_config = {"from_attributes": True}
