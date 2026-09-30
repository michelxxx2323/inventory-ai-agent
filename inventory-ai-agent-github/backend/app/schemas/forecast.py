# inventory ai agent/backend/app/schemas/forecast.py
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date

# Base Forecast properties
class ForecastBase(BaseModel):
    """Base schema for forecast data"""
    product_id: int = Field(..., gt=0, description="ID of the product being forecasted")
    store_id: int = Field(..., gt=0, description="ID of the store")
    retailer_id: int = Field(..., gt=0, description="ID of the retailer (for RLS)")
    period: str = Field(..., pattern="^[0-9]+d$", description="Forecast period (e.g., '30d', '60d')")
    predicted_demand: float = Field(..., ge=0, description="Predicted demand for the period")
    recommended_stock: int = Field(..., ge=0, description="Recommended stock level")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score of the prediction")
    model_metrics: Optional[Dict[str, Union[float, int, str]]] = Field(
        None,
        description="Model metrics like MAE, RMSE, etc."
    )

    model_config = ConfigDict(from_attributes=True)

    @validator('period')
    def validate_period(cls, v):
        """Validate period format (e.g., '30d')"""
        if not v.endswith('d') or not v[:-1].isdigit():
            raise ValueError("Period must be in format 'Nd' where N is a number")
        days = int(v[:-1])
        if days <= 0:
            raise ValueError("Period must be positive")
        return v

    @validator('model_metrics')
    def validate_metrics(cls, v):
        """Validate model metrics structure"""
        if v is not None:
            # Ensure all numeric values are floats
            for key, value in v.items():
                if isinstance(value, (int, float)):
                    v[key] = float(value)
        return v

# Schema for creating a new forecast record (usually done internally)
class ForecastCreate(ForecastBase):
    """Schema for creating a new forecast"""
    pass

# Schema for updating (less common for forecasts, maybe only metrics?)
class ForecastUpdate(BaseModel):
    """Schema for updating an existing forecast"""
    predicted_demand: Optional[float] = Field(None, ge=0)
    recommended_stock: Optional[int] = Field(None, ge=0)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    model_metrics: Optional[Dict[str, Union[float, int, str]]] = None

    model_config = ConfigDict(from_attributes=True)

# Schema for reading/returning forecast data
class ForecastRead(ForecastBase):
    """Schema for reading forecast data"""
    id: int
    created_at: datetime
    updated_at: datetime

# Schema for requesting a forecast generation
class ForecastInput(BaseModel):
    """Schema for forecast generation request"""
    product_id: int = Field(..., gt=0, description="ID of the product to forecast")
    store_id: int = Field(..., gt=0, description="ID of the store")
    period: str = Field(
        ...,
        pattern="^[0-9]+d$",
        description="Forecast period (e.g., '30d', '60d')",
        example="30d"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "product_id": 1,
            "store_id": 1,
            "period": "30d"
        }
    })

    @validator('period')
    def validate_period(cls, v):
        """Validate period format (e.g., '30d')"""
        if not v.endswith('d') or not v[:-1].isdigit():
            raise ValueError("Period must be in format 'Nd' where N is a number")
        days = int(v[:-1])
        if days <= 0:
            raise ValueError("Period must be positive")
        return v 