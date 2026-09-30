import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

from app.services.forecast import ForecastService
from app.services.product import ProductService
from app.services.inventory import InventoryService
from app.schemas.forecast import ForecastRequest, ForecastRead
from app.models.forecast import Forecast
from app.core.database import get_supabase

# Load test environment variables
load_dotenv('.env.test')

# --- Test Fixtures ---

@pytest.fixture
async def supabase_client():
    """Get real Supabase client for testing."""
    client = get_supabase()
    # Clean up test data before each test
    await client.table("forecasts").delete().execute()
    return client

@pytest.fixture
def mock_product_service():
    """Mock ProductService with necessary methods."""
    service = MagicMock(spec=ProductService)
    
    # Mock get_historical_sales method with realistic test data
    async def mock_get_sales(product_id: int, days_history: int = 365) -> list:
        # Generate sample historical sales data with a realistic pattern
        dates = pd.date_range(end=datetime.now(), periods=days_history)
        # Create sales with weekly seasonality and trend
        t = np.arange(len(dates))
        trend = 0.1 * t  # Slight upward trend
        weekly = 20 * np.sin(2 * np.pi * t / 7)  # Weekly seasonality
        noise = np.random.normal(0, 5, len(dates))  # Random noise
        sales = 50 + trend + weekly + noise  # Base demand of 50
        sales = np.maximum(sales, 0)  # Ensure non-negative
        return [{"date": d.date(), "quantity": int(q)} for d, q in zip(dates, sales)]
    
    service.get_historical_sales = AsyncMock(side_effect=mock_get_sales)
    return service

@pytest.fixture
def mock_inventory_service():
    """Mock InventoryService with necessary methods."""
    service = MagicMock(spec=InventoryService)
    
    # Mock get_by_product_store method with realistic inventory data
    async def mock_get_inventory(product_id: int, store_id: int):
        return MagicMock(current_stock=50)  # Realistic current stock level
    
    service.get_by_product_store = AsyncMock(side_effect=mock_get_inventory)
    return service

@pytest.fixture
def forecast_service(supabase_client, mock_product_service, mock_inventory_service):
    """Create ForecastService instance with real Supabase."""
    service = ForecastService(
        product_service=mock_product_service,
        inventory_service=mock_inventory_service
    )
    service.client = supabase_client
    return service

# --- Sample Data ---

SAMPLE_PRODUCT_ID = 1
SAMPLE_STORE_ID = 1

# --- Test Cases ---

@pytest.mark.asyncio
async def test_generate_and_store_forecast_success(forecast_service):
    """Test successful forecast generation and storage with real Supabase."""
    request = ForecastRequest(
        product_id=SAMPLE_PRODUCT_ID,
        store_id=SAMPLE_STORE_ID,
        forecast_horizon_days=30
    )
    
    # Generate forecast
    result = await forecast_service.generate_and_store_forecast(request)
    
    # Verify the forecast was actually stored in Supabase
    stored_forecast = await forecast_service.client.table("forecasts")\
        .select("*")\
        .eq("product_id", SAMPLE_PRODUCT_ID)\
        .eq("store_id", SAMPLE_STORE_ID)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    
    assert stored_forecast.data is not None
    assert len(stored_forecast.data) == 1
    assert stored_forecast.data[0]["product_id"] == SAMPLE_PRODUCT_ID

@pytest.mark.asyncio
async def test_generate_and_store_forecast_insufficient_data(forecast_service):
    """Test forecast generation with insufficient historical data."""
    # Override mock to return insufficient data
    forecast_service.product_service.get_historical_sales.return_value = [
        {"date": date.today() - timedelta(days=i), "quantity": 10}
        for i in range(5)  # Only 5 days of data
    ]
    
    request = ForecastRequest(
        product_id=SAMPLE_PRODUCT_ID,
        store_id=SAMPLE_STORE_ID,
        forecast_horizon_days=30
    )
    
    # Assert that it raises ValueError for insufficient data
    with pytest.raises(ValueError) as exc_info:
        await forecast_service.generate_and_store_forecast(request)
    assert "Insufficient historical sales data" in str(exc_info.value)

@pytest.mark.asyncio
async def test_generate_and_store_forecast_with_custom_parameters(forecast_service):
    """Test forecast generation with custom parameters."""
    request = ForecastRequest(
        product_id=SAMPLE_PRODUCT_ID,
        store_id=SAMPLE_STORE_ID,
        forecast_horizon_days=30,
        parameters_override={"daily_seasonality": False}
    )
    
    result = await forecast_service.generate_and_store_forecast(request)
    
    assert result is not None
    assert result.model_parameters.get("daily_seasonality") is False
    
    # Verify in Supabase
    stored_forecast = await forecast_service.client.table("forecasts")\
        .select("*")\
        .eq("id", result.id)\
        .limit(1)\
        .execute()
    
    assert stored_forecast.data is not None
    assert len(stored_forecast.data) == 1
    assert stored_forecast.data[0]["model_parameters"].get("daily_seasonality") is False

@pytest.mark.asyncio
async def test_cleanup(supabase_client):
    """Clean up test data after all tests."""
    await supabase_client.table("forecasts").delete().execute()

if __name__ == "__main__":
    pytest.main(["-v", "test_forecast_service.py"]) 