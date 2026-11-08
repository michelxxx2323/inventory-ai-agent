# inventory ai agent/backend/app/schemas/product.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# Base properties shared by create and update schemas
class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    sku: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    base_price: float
    current_price: float
    cost_price: float
    weight: Optional[float] = None # in kg
    dimensions: Optional[Dict[str, Any]] = None # {length, width, height} in cm
    barcode: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    minimum_stock: int = 0
    maximum_stock: int = 1000
    reorder_point: int = 10
    lead_time_days: int = 7
    shopify_product_id: Optional[str] = Field(None, max_length=100)
    erp_product_id: Optional[str] = Field(None, max_length=100)
    # retailer_id is handled separately in the service layer during creation

    class Config:
        orm_mode = True # For compatibility if needed later

# Schema for creating a new product (requires retailer_id externally)
class ProductCreate(ProductBase):
    pass # Inherits all fields from ProductBase

# Schema for updating an existing product (all fields optional)
class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, max_length=255)
    sku: Optional[str] = Field(None, max_length=100) # Usually SKU shouldn't be updated, but allowed here
    base_price: Optional[float] = None
    current_price: Optional[float] = None
    cost_price: Optional[float] = None
    is_active: Optional[bool] = None
    minimum_stock: Optional[int] = None
    maximum_stock: Optional[int] = None
    reorder_point: Optional[int] = None
    lead_time_days: Optional[int] = None
    # retailer_id should not be updatable

    class Config:
       orm_mode = True # For compatibility if needed later


# Schema for reading/returning product data (includes ID and retailer_id)
class ProductRead(ProductBase):
    id: int
    retailer_id: int
    created_at: datetime
    updated_at: datetime 