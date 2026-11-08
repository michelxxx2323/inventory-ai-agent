from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Dict, Any, List, Optional
from datetime import date, datetime

from .core.config import settings
from .core.database import get_supabase, supabase
from .services.retailer import RetailerService
from .services.product import ProductService
from .services.inventory import InventoryService
from .services.forecast import ForecastService
from .schemas.product import ProductCreate, ProductUpdate, ProductRead
from .schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryRead, InventoryAdjust,
    InventoryHistoryRead, InventoryHistoryQuery
)
from .schemas.forecast import ForecastCreate, ForecastUpdate, ForecastRequest, ForecastRead

# Create FastAPI app
app = FastAPI(
    title="AI Inventory Agent",
    description="AI-powered inventory management system for small retailers",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (Order matters due to injection)
retailer_service = RetailerService()
product_service = ProductService()
inventory_service = InventoryService()
# Inject dependencies into ForecastService
forecast_service = ForecastService(product_service=product_service, inventory_service=inventory_service)

@app.get("/")
async def root():
    """Root endpoint returning API status"""
    return JSONResponse(
        content={
            "status": "online",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
    )

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint testing database connectivity"""
    try:
        # Test database connection by counting retailers
        retailer_count = await retailer_service.count()
        
        # Test Supabase connection
        supabase_status = "connected" if supabase else "disconnected"
        
        return {
            "status": "healthy",
            "services": {
                "api": "operational",
                "database": {
                    "status": supabase_status,
                    "retailer_count": retailer_count
                }
            },
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/api/v1/retailers/count")
async def get_retailer_count():
    """Get total number of retailers"""
    try:
        count = await retailer_service.count()
        return {"count": count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get retailer count: {str(e)}"
        )

@app.get("/api/v1/retailers/{retailer_id}/products/{sku}", response_model=ProductRead, tags=["Products"])
async def get_product_by_sku_for_retailer(retailer_id: int, sku: str):
    """
    Get product details by SKU for a specific retailer.
    """
    try:
        product = await product_service.get_by_sku(retailer_id=retailer_id, sku=sku)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found for this retailer")
        # Convert Product model to ProductRead schema before returning
        # This might happen implicitly if Pydantic handles ORM mode, or requires manual conversion
        # Let's assume Pydantic handles it for now, adjust if validation errors occur
        return product
    except ValueError as ve: # Catch specific errors like missing ID if raised
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Log the exception details for debugging
        print(f"Error in get_product_by_sku_for_retailer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product: {str(e)}"
        )

@app.post("/api/v1/retailers/{retailer_id}/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def sync_product(retailer_id: int, product_data: ProductCreate):
    """
    Create a new product or update an existing one based on SKU for a specific retailer.
    - Returns 201 Created if a new product is created.
    - Returns 200 OK if an existing product is updated.
    """
    try:
        # Check existence first to determine potential status code
        existing = await product_service.get_by_sku(retailer_id, product_data.sku)
        
        product = await product_service.create_or_update_product(retailer_id=retailer_id, data=product_data)

        if product is None:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create or update product")

        # Determine status code - NOTE: FastAPI might not dynamically change the code from the decorator
        # We might need to return a JSONResponse directly if strict 200 vs 201 is needed.
        # For simplicity, documentation indicates behavior; actual code might be 201 or 200.
        response_status_code = status.HTTP_200_OK if existing else status.HTTP_201_CREATED

        # Return the product. Pydantic should convert to ProductRead.
        # To ensure correct status code, one could do: 
        # return JSONResponse(content=ProductRead.from_orm(product).dict(), status_code=response_status_code)
        # But let's rely on decorator + documentation for now.
        return product

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error in sync_product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync product: {str(e)}"
        )

@app.get("/api/v1/stores/{store_id}/products", response_model=List[ProductRead], tags=["Products", "Stores"])
async def list_products_by_store(store_id: int):
    """
    Get a list of products available in a specific store.
    """
    try:
        products = await product_service.get_products_by_store(store_id=store_id)
        # Assuming Pydantic handles the conversion of List[Product] to List[ProductRead]
        return products
    except Exception as e:
        print(f"Error in list_products_by_store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products for store {store_id}: {str(e)}"
        )

@app.put("/api/v1/products/{product_id}", response_model=ProductRead, tags=["Products"])
async def update_existing_product(product_id: int, product_data: ProductUpdate):
    """
    Update an existing product by its ID.
    """
    try:
        updated_product = await product_service.update_product(product_id=product_id, product_data=product_data)
        if updated_product is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found or failed to update.")
        return updated_product # Pydantic converts to ProductRead
    except ValueError as ve: # e.g., invalid data
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error in update_existing_product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product {product_id}: {str(e)}"
        )

@app.delete("/api/v1/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
async def remove_product(product_id: int):
    """
    Delete a product by its ID.
    Returns 204 No Content on success.
    """
    try:
        deleted = await product_service.delete_product(product_id=product_id)
        if not deleted:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")
        # No return body needed for 204
        return None
    except Exception as e:
        print(f"Error in remove_product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product {product_id}: {str(e)}"
        )

@app.get("/api/v1/products/top-sellers", response_model=List[ProductRead], tags=["Products"])
async def get_top_sellers(limit: int = 5, days: int = 7):
    """Get top selling products"""
    try:
        top_sellers = await product_service.list_top_sellers(limit=limit, days=days)
        # Assuming list_top_sellers returns data that can be parsed into List[ProductRead]
        # This might require modification in the service or explicit conversion here
        return top_sellers
    except Exception as e:
        print(f"Error getting top sellers: {e}") # Added logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top sellers: {str(e)}"
        )

@app.get("/api/v1/stores/{store_id}/products/{product_id}/forecasts", response_model=List[ForecastRead], tags=["Forecasts"])
async def get_product_store_forecasts(
    store_id: int,
    product_id: int,
    start_after: Optional[date] = Query(None, description="Optional filter to get forecasts starting after this date.")
):
    """Retrieve forecasts for a specific product at a specific store."""
    try:
        forecasts = await forecast_service.get_forecasts_for_product_store(
            product_id=product_id, store_id=store_id, start_after=start_after
        )
        # Pydantic should handle conversion List[Forecast] -> List[ForecastRead]
        return forecasts
    except Exception as e:
        # Log the error
        print(f"Error getting forecasts for product {product_id}, store {store_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecasts: {str(e)}"
        )

@app.get("/api/v1/stores/{store_id}/products/{product_id}/forecasts/latest", response_model=ForecastRead, tags=["Forecasts"])
async def get_latest_product_store_forecast(store_id: int, product_id: int):
    """Retrieve the single most recent forecast for a specific product at a specific store."""
    try:
        forecast = await forecast_service.get_latest_forecast(product_id=product_id, store_id=store_id)
        if forecast is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No forecast found for this product/store combination.")
        # Pydantic should handle conversion Forecast -> ForecastRead
        return forecast
    except Exception as e:
        print(f"Error getting latest forecast for product {product_id}, store {store_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest forecast: {str(e)}"
        )

@app.post("/api/v1/forecasts/generate", response_model=ForecastRead, status_code=status.HTTP_201_CREATED, tags=["Forecasts"])
async def request_forecast_generation(request_body: ForecastRequest):
    """
    Request the generation and storage of a new forecast based on the provided parameters.
    This is likely an asynchronous operation trigger; the response confirms storage.
    """
    try:
        new_forecast = await forecast_service.generate_and_store_forecast(request=request_body)
        if new_forecast is None:
             # Check logs in service for reason (model failure vs storage failure)
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Forecast generation or storage failed.")
        # Pydantic converts Forecast -> ForecastRead
        return new_forecast
    except ValueError as ve: # Catch specific errors like model failure if raised
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error processing forecast generation request {request_body}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process forecast generation request: {str(e)}"
        )

@app.patch("/api/v1/forecasts/{forecast_id}/metrics", response_model=ForecastRead, tags=["Forecasts"])
async def update_forecast_performance_metrics(forecast_id: int, metrics_update: ForecastUpdate):
    """Update performance metrics (e.g., accuracy, MAPE) for an existing forecast."""
    try:
        updated_forecast = await forecast_service.update_forecast_metrics(forecast_id=forecast_id, update_data=metrics_update)
        if updated_forecast is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast with ID {forecast_id} not found or update failed.")
        # Pydantic converts Forecast -> ForecastRead
        return updated_forecast
    except ValueError as ve:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error updating metrics for forecast {forecast_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update forecast metrics: {str(e)}"
        )

@app.delete("/api/v1/forecasts/{forecast_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Forecasts"])
async def remove_forecast(forecast_id: int):
    """Delete a specific forecast record by its ID."""
    try:
        deleted = await forecast_service.delete_forecast(forecast_id=forecast_id)
        if not deleted:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast with ID {forecast_id} not found.")
        # No content response
        return None
    except Exception as e:
        print(f"Error deleting forecast {forecast_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete forecast: {str(e)}"
        )

@app.get("/api/v1/stores/{store_id}/products/{product_id}/inventory", response_model=InventoryRead, tags=["Inventory"])
async def get_specific_inventory_item(store_id: int, product_id: int):
    """Retrieve the inventory record for a specific product at a specific store."""
    try:
        inventory_item = await inventory_service.get_by_product_store(product_id=product_id, store_id=store_id)
        if inventory_item is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found for this product/store combination.")
        # Pydantic handles Inventory -> InventoryRead
        return inventory_item
    except Exception as e:
        print(f"Error getting inventory for product {product_id}, store {store_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inventory record: {str(e)}"
        )

@app.get("/api/v1/stores/{store_id}/inventory", response_model=List[InventoryRead], tags=["Inventory"])
async def get_store_inventory(store_id: int):
    """Retrieve all inventory records for a specific store."""
    try:
        # Service method get_inventory_for_store returns List[Dict]
        # We need to convert these dicts to InventoryRead schema
        inventory_data_list = await inventory_service.get_inventory_for_store(store_id=store_id, include_product=False) # Let's not include product for now
        # Manual conversion needed as service returns raw dicts
        # Need careful parsing, ensure dict matches InventoryRead fields
        inventory_read_list = []
        for item in inventory_data_list:
            try:
                inventory_read_list.append(InventoryRead(**item))
            except Exception as parse_error:
                print(f"Error parsing inventory item for store {store_id}: {parse_error}, data: {item}")
                # Skip faulty items or raise 500?
                # For now, skip and log
                continue
        return inventory_read_list
    except Exception as e:
        print(f"Error getting inventory for store {store_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve store inventory: {str(e)}"
        )

@app.get("/api/v1/products/{product_id}/inventory", response_model=List[InventoryRead], tags=["Inventory"])
async def get_product_inventory_across_stores(product_id: int):
    """Retrieve all inventory records for a specific product across all stores."""
    try:
        inventory_list = await inventory_service.get_inventory_for_product(product_id=product_id)
        # Pydantic handles List[Inventory] -> List[InventoryRead]
        return inventory_list
    except Exception as e:
        print(f"Error getting inventory for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve product inventory: {str(e)}"
        )

@app.post("/api/v1/inventory", response_model=InventoryRead, status_code=status.HTTP_201_CREATED, tags=["Inventory"])
async def create_new_inventory_record(inventory_data: InventoryCreate):
    """Create a new inventory record (e.g., when adding a product to a store for the first time)."""
    try:
        new_item = await inventory_service.create_inventory_item(inventory_data=inventory_data)
        if new_item is None:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create inventory record.")
        return new_item # Pydantic handles conversion
    except ValueError as ve: # Catch duplicates or validation errors from service
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve)) # 409 Conflict for duplicates
    except Exception as e:
        print(f"Error creating inventory record {inventory_data}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inventory record: {str(e)}"
        )

@app.put("/api/v1/inventory/{inventory_id}", response_model=InventoryRead, tags=["Inventory"])
async def update_inventory_record(inventory_id: int, inventory_data: InventoryUpdate):
    """Update details of an existing inventory record."""
    try:
        updated_item = await inventory_service.update_inventory_item(inventory_id=inventory_id, inventory_data=inventory_data)
        if updated_item is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inventory record with ID {inventory_id} not found or update failed.")
        return updated_item # Pydantic handles conversion
    except ValueError as ve: # Catch validation errors from service
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error updating inventory record {inventory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update inventory record: {str(e)}"
        )

@app.patch("/api/v1/inventory/{inventory_id}/adjust", response_model=InventoryRead, tags=["Inventory"])
async def adjust_inventory_stock(inventory_id: int, adjustment_data: InventoryAdjust):
    """Adjust the stock quantity (current and available) for an inventory record."""
    try:
        adjusted_item = await inventory_service.adjust_stock(inventory_id=inventory_id, adjustment=adjustment_data)
        if adjusted_item is None:
             # Service should raise ValueError if not found, this handles other update failures
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to apply stock adjustment.")
        return adjusted_item # Pydantic handles conversion
    except ValueError as ve: # Catch not found or negative stock errors
        # Determine status code based on error message?
        if "not found" in str(ve).lower():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        else:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error adjusting stock for inventory record {inventory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to adjust inventory stock: {str(e)}"
        )

@app.delete("/api/v1/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Inventory"])
async def remove_inventory_record(inventory_id: int):
    """Delete a specific inventory record by its ID."""
    try:
        deleted = await inventory_service.delete_inventory_item(inventory_id=inventory_id)
        if not deleted:
             # Could be not found or deletion failed
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inventory record with ID {inventory_id} not found or deletion failed.")
        # No content response
        return None
    except ValueError as ve: # Catch specific errors like "cannot delete with positive stock"
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"Error deleting inventory record {inventory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete inventory record: {str(e)}"
        )

@app.get(
    "/api/v1/inventories/{inventory_id}/history",
    response_model=List[InventoryHistoryRead],
    tags=["Inventory"],
    summary="Get inventory history records",
    description="Retrieve history of stock changes for a specific inventory item with optional date filtering"
)
async def get_inventory_history(
    inventory_id: int,
    start_date: Optional[datetime] = Query(
        None,
        description="Filter records after this date (ISO format)",
        example="2024-03-20T00:00:00Z"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter records before this date (ISO format)",
        example="2024-03-21T00:00:00Z"
    )
):
    """
    Retrieve the history of stock changes for a specific inventory item.
    
    Args:
        inventory_id: The ID of the inventory record
        start_date: Optional start date for filtering records
        end_date: Optional end date for filtering records
        
    Returns:
        List of inventory history records ordered by changed_at descending
        
    Raises:
        404: If inventory_id is not found
        400: If date range is invalid
        500: For other errors
    """
    try:
        # Validate date range if both dates are provided
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be after start_date")
            
        # Get history records
        history_records = await inventory_service.get_stock_history(
            inventory_id=inventory_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # If no records found but inventory exists, return empty list
        # If inventory doesn't exist, get_stock_history would have raised ValueError
        return history_records
        
    except ValueError as ve:
        if "Invalid inventory_id" in str(ve):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory record with ID {inventory_id} not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )
    except Exception as e:
        print(f"Error fetching inventory history for inventory {inventory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inventory history: {str(e)}"
        )

@app.get(
    "/api/v1/forecasts/{forecast_id}/accuracy",
    response_model=Dict[str, float],
    tags=["Forecasts"],
    summary="Evaluate forecast accuracy",
    description="Evaluates the accuracy of a forecast by comparing predicted values with actual sales data. Updates and returns the model metrics."
)
async def evaluate_forecast_accuracy(
    forecast_id: int = Path(..., gt=0, description="The ID of the forecast to evaluate"),
):
    """
    Evaluates the accuracy of a forecast by comparing predicted values with actual sales.
    
    Args:
        forecast_id: The ID of the forecast to evaluate
        
    Returns:
        Dict[str, float]: Updated model metrics including MAE, RMSE, and other accuracy measures
        
    Raises:
        404: If forecast not found
        400: If evaluation fails due to insufficient data
        500: For other errors
    """
    try:
        # Evaluate forecast accuracy
        updated_forecast = await forecast_service.evaluate_forecast_accuracy(forecast_id)
        
        if not updated_forecast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forecast with ID {forecast_id} not found"
            )
            
        # Extract numeric metrics only
        numeric_metrics = {}
        if updated_forecast.model_metrics:
            for key, value in updated_forecast.model_metrics.items():
                if isinstance(value, (int, float)):
                    numeric_metrics[key] = float(value)
                    
        if not numeric_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No numeric metrics available. This may be due to insufficient sales data for comparison."
            )
            
        logger.info(f"Successfully evaluated accuracy for forecast {forecast_id}")
        return numeric_metrics
        
    except ValueError as ve:
        # Handle specific validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error evaluating forecast {forecast_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate forecast accuracy: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 