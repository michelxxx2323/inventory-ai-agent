# inventory ai agent/backend/app/schemas/inventory.py
from pydantic import BaseModel, Field, validator # Add validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# Base Inventory properties
class InventoryBase(BaseModel):
    product_id: int
    store_id: int
    current_stock: int = Field(..., ge=0) # Cannot be negative
    available_stock: Optional[int] = None # Often calculated, but allow setting
    reserved_stock: int = Field(default=0, ge=0)
    storage_location: Optional[str] = Field(None, max_length=50)
    stock_history: Optional[List[Dict[str, Any]]] = None # e.g., [{"timestamp": "...", "stock": 10}]
    daily_sales_velocity: float = 0.0
    weekly_sales_velocity: float = 0.0
    monthly_sales_velocity: float = 0.0

    class Config:
        orm_mode = True

# Schema for creating a new inventory record
class InventoryCreate(InventoryBase):
     # When creating, available_stock might default to current_stock if not provided
    available_stock: Optional[int] = None

    @validator('available_stock', pre=True, always=True)
    def set_available_stock(cls, v, values):
        # If available_stock is not provided and current_stock exists, default it to current_stock
        # Check 'current_stock' in values as validation order might matter
        if v is None and 'current_stock' in values and values.get('current_stock') is not None:
             current_stock = values['current_stock']
             # Ensure reserved_stock is considered if provided, otherwise default to 0
             reserved_stock = values.get('reserved_stock', 0)
             calculated_available = current_stock - reserved_stock
             return max(0, calculated_available) # Ensure available stock is not negative
        elif v is not None and 'current_stock' in values and 'reserved_stock' in values:
             # Validate if available_stock is manually provided
             if values.get('current_stock') is None or values.get('reserved_stock') is None:
                 # Cannot validate if dependent fields are missing
                 return v # Allow it for now, service layer should handle final state
             if v > values['current_stock'] - values.get('reserved_stock', 0):
                 raise ValueError("available_stock cannot exceed current_stock minus reserved_stock")
             if v < 0:
                 raise ValueError("available_stock cannot be negative")
        return v # Return the provided value if it's valid or None if current_stock isn't set yet


# Schema for updating an existing inventory record (all fields optional)
class InventoryUpdate(BaseModel):
    current_stock: Optional[int] = Field(None, ge=0)
    available_stock: Optional[int] = Field(None, ge=0) # Validation needed (e.g., in service layer)
    reserved_stock: Optional[int] = Field(None, ge=0)
    storage_location: Optional[str] = Field(None, max_length=50)
    stock_history: Optional[List[Dict[str, Any]]] = None
    daily_sales_velocity: Optional[float] = None
    weekly_sales_velocity: Optional[float] = None
    monthly_sales_velocity: Optional[float] = None
    # product_id and store_id should generally not be updated

    class Config:
        orm_mode = True

# Schema for reading/returning inventory data
class InventoryRead(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Potentially include nested Product/Store info if needed
    # product: Optional[ProductRead] = None # Requires ProductRead schema import
    # store: Optional[StoreRead] = None # Requires StoreRead schema import


# Schema for adjusting stock quantity
class InventoryAdjust(BaseModel):
    quantity_change: int # Positive for increase, negative for decrease
    reason: Optional[str] = Field(None, description="Reason for adjustment (e.g., 'stocktake', 'damage', 'return')")

# Base schema for inventory history
class InventoryHistoryBase(BaseModel):
    """Base schema for inventory history records"""
    inventory_id: int = Field(..., description="ID of the inventory record")
    product_id: int = Field(..., description="ID of the product")
    store_id: int = Field(..., description="ID of the store")
    retailer_id: int = Field(..., description="ID of the retailer")
    old_stock: int = Field(..., ge=0, description="Previous stock level")
    new_stock: int = Field(..., ge=0, description="New stock level")
    changed_by: str = Field(..., description="User or system that made the change")
    reason: Optional[str] = Field(None, description="Reason for the stock change")

    @validator('new_stock', 'old_stock')
    def validate_stock_values(cls, v):
        if v < 0:
            raise ValueError("Stock values cannot be negative")
        return v

    class Config:
        orm_mode = True

# Schema for creating inventory history records
class InventoryHistoryCreate(InventoryHistoryBase):
    """Schema for creating new inventory history records"""
    changed_at: datetime = Field(default_factory=datetime.utcnow)

# Schema for reading inventory history records
class InventoryHistoryRead(InventoryHistoryBase):
    """Schema for reading inventory history records"""
    id: int
    changed_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "inventory_id": 1,
                "product_id": 1,
                "store_id": 1,
                "retailer_id": 1,
                "old_stock": 100,
                "new_stock": 90,
                "changed_by": "john.doe@example.com",
                "changed_at": "2024-03-20T10:00:00Z",
                "reason": "Sale completed"
            }
        }

# Schema for querying inventory history
class InventoryHistoryQuery(BaseModel):
    """Schema for querying inventory history records"""
    inventory_id: Optional[int] = None
    product_id: Optional[int] = None
    store_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError("end_date must be after start_date")
        return v 