from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import logging
import pandas as pd
import numpy as np

from .base import BaseService
from ..models.forecast import Forecast
from ..schemas.forecast import ForecastCreate, ForecastUpdate, ForecastRequest, ForecastRead
# Add imports for injected services
from .product import ProductService
from .inventory import InventoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Make sure prophet is installed: pip install prophet
try:
    from prophet import Prophet
except ImportError:
    logger.error("Prophet library not installed. Please install it: pip install prophet")
    # Raise an error or provide a fallback mechanism if Prophet is optional
    Prophet = None
from sklearn.metrics import mean_absolute_error # For MAE calculation

class ForecastService(BaseService[Forecast]):
    """Service for demand forecast operations"""

    def __init__(self, product_service: ProductService, inventory_service: InventoryService):
        super().__init__("forecasts")
        self.product_service = product_service
        self.inventory_service = inventory_service
        # Initialize connections to ML models or data sources if needed
        # self.ml_model_client = ...

    async def _instantiate_forecast(self, data: Dict[str, Any]) -> Optional[Forecast]:
        """Safely instantiate Forecast model from dict."""
        try:
            # Convert date strings to date objects if needed
            if isinstance(data.get('start_date'), str):
                data['start_date'] = date.fromisoformat(data['start_date'])
            if isinstance(data.get('end_date'), str):
                data['end_date'] = date.fromisoformat(data['end_date'])
            # Convert datetime strings if needed (e.g., created_at, updated_at from base model)
            if isinstance(data.get('created_at'), str):
                 data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) # Handle Z timezone
            if isinstance(data.get('updated_at'), str):
                 data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            return Forecast(**data)
        except TypeError as e:
            logger.error(f"Error instantiating Forecast model (TypeError): {e}, data: {data}")
            return None
        except ValueError as e:
            logger.error(f"Error instantiating Forecast model (ValueError/DateParse): {e}, data: {data}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error instantiating Forecast model: {e}, data: {data}")
            return None

    async def get_forecasts_for_product_store(self, product_id: int, store_id: int, start_after: Optional[date] = None) -> List[Forecast]:
        """Get all forecasts for a specific product and store, optionally after a certain date."""
        try:
            query = self.client.table(self.table_name)\
                .select("*")\
                .eq("product_id", product_id)\
                .eq("store_id", store_id)\
                .order("start_date", desc=True) # Get newest first

            if start_after:
                 query = query.gt("start_date", start_after.isoformat())

            result = await query.execute()

            forecast_list = []
            if result.data:
                for item_data in result.data:
                    forecast_item = await self._instantiate_forecast(item_data)
                    if forecast_item:
                        forecast_list.append(forecast_item)
            return forecast_list
        except Exception as e:
            logger.error(f"Error fetching forecasts for product {product_id}, store {store_id}: {e}")
            raise e # Or return []

    async def get_latest_forecast(self, product_id: int, store_id: int) -> Optional[Forecast]:
        """Get the most recent forecast for a specific product and store."""
        try:
            result = await self.client.table(self.table_name)\
                .select("*")\
                .eq("product_id", product_id)\
                .eq("store_id", store_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if result.data:
                return await self._instantiate_forecast(result.data[0])
            return None
        except Exception as e:
             logger.error(f"Error fetching latest forecast for product {product_id}, store {store_id}: {e}")
             raise e # Or return None

    async def generate_and_store_forecast(self, product_id: int, store_id: int, period: str) -> Optional[ForecastRead]:
        """
        Generates a demand forecast using Prophet, stores it, and returns the result.
        
        Args:
            product_id (int): ID of the product to forecast
            store_id (int): ID of the store
            period (str): Forecast period (e.g., "30d", "60d", "90d")
            
        Returns:
            ForecastRead: Forecast data if successful
            
        Raises:
            ValueError: If historical data is insufficient or inputs are invalid
            RuntimeError: If Prophet is not installed
        """
        if Prophet is None:
            raise RuntimeError("Prophet library is required but not installed.")
            
        # Extract days from period string
        try:
            horizon_days = int(period.replace('d', ''))
        except ValueError:
            raise ValueError(f"Invalid period format: {period}. Expected format: '30d', '60d', etc.")

        logger.info(f"Starting forecast generation for product {product_id}, store {store_id}, horizon {horizon_days} days.")

        # --- 1. Fetch Required Data ---
        try:
            # Get historical sales data
            sales_history = await self.product_service.get_historical_sales(product_id, days_history=horizon_days)
            if not sales_history or len(sales_history) < 7:  # Need at least a week of data
                raise ValueError(f"Insufficient historical sales data for product {product_id}")

            # Get current stock and retailer_id
            inventory_item = await self.inventory_service.get_by_product_store(product_id, store_id)
            if not inventory_item:
                raise ValueError(f"No inventory record found for product {product_id} in store {store_id}")
            current_stock = inventory_item.current_stock
            
            # Get retailer_id from product service
            product = await self.product_service.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
            retailer_id = product.retailer_id

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise

        # --- 2. Prepare Training Data ---
        try:
            df = pd.DataFrame(sales_history)
            df['ds'] = pd.to_datetime(df['date'])
            df['y'] = df['quantity'].astype(float)
            df = df[['ds', 'y']].sort_values('ds')
            logger.info(f"Prepared DataFrame with {len(df)} historical data points")
        except Exception as e:
            logger.error(f"Error preparing DataFrame: {e}")
            raise ValueError("Failed to process historical sales data")

        # --- 3. Calculate Historical MAE ---
        mae = None
        if len(df) >= 30:  # Need at least 30 days for MAE calculation
            try:
                # Use last 30 days as validation set
                validation_df = df.tail(30)
                training_df = df.head(len(df) - 30)
                
                # Fit model on training data
                mae_model = Prophet(daily_seasonality=True)
                mae_model.fit(training_df)
                
                # Predict validation period
                future_df = mae_model.make_future_dataframe(periods=30)
                forecast_df = mae_model.predict(future_df)
                
                # Calculate MAE
                predictions = forecast_df.tail(30)['yhat'].values
                actuals = validation_df['y'].values
                mae = float(mean_absolute_error(actuals, predictions))
                logger.info(f"Calculated MAE: {mae:.2f}")
            except Exception as e:
                logger.warning(f"Could not calculate MAE: {e}")

        # --- 4. Fit Prophet Model and Generate Forecast ---
        try:
            # Initialize and fit model
            model = Prophet(daily_seasonality=True)
            model.fit(df)
            
            # Generate future dates and predict
            future_df = model.make_future_dataframe(periods=horizon_days)
            forecast_df = model.predict(future_df)
            
            # Extract predictions for the forecast period
            predictions = forecast_df.tail(horizon_days)
            
            # Calculate total predicted demand
            predicted_demand = int(round(predictions['yhat'].sum()))
            
            # Calculate confidence score (1 = most confident)
            uncertainty_ratios = (predictions['yhat_upper'] - predictions['yhat_lower']) / predictions['yhat']
            confidence_score = float(1 - np.clip(uncertainty_ratios.mean(), 0, 1))
            
            # Calculate recommended stock with 10% buffer
            buffer = predicted_demand * 0.10
            recommended_stock = max(0, int(round(predicted_demand + buffer - current_stock)))
            
            # Prepare forecast details
            forecast_data = {
                "daily_predictions": predictions[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict('records')
            }
            
            # Prepare model metrics
            model_metrics = {
                "mae_30d": mae if mae is not None else None,
                "training_samples": len(df),
                "forecast_horizon": horizon_days
            }

        except Exception as e:
            logger.error(f"Error in Prophet modeling: {e}")
            raise ValueError(f"Failed to generate forecast: {e}")

        # --- 5. Create and Store Forecast ---
        try:
            forecast_create = ForecastCreate(
                product_id=product_id,
                store_id=store_id,
                retailer_id=retailer_id,
                start_date=predictions['ds'].min().date(),
                end_date=predictions['ds'].max().date(),
                period_type=period,
                predicted_demand=predicted_demand,
                confidence_score=confidence_score,
                forecast_data=forecast_data,
                recommended_stock=recommended_stock,
                recommended_actions=["Order recommended stock"] if recommended_stock > 0 else ["Monitor stock levels"],
                model_version=f"prophet_{pd.__version__}",
                model_parameters={"daily_seasonality": True},
                model_metrics=model_metrics
            )

            # Store forecast in database
            created_response = await self.create(forecast_create.dict())
            if not created_response or not created_response.data:
                raise ValueError("Failed to store forecast in database")

            # Convert stored data to Forecast model
            new_forecast = await self._instantiate_forecast(created_response.data[0])
            if not new_forecast:
                raise ValueError("Failed to process saved forecast data")

            logger.info(f"Successfully stored forecast for product {product_id}, store {store_id}")
            return ForecastRead.from_orm(new_forecast)

        except Exception as e:
            logger.error(f"Error storing forecast: {e}")
            raise

    # Update method might be used for adding back-tested accuracy metrics later
    async def update_forecast_metrics(self, forecast_id: int, update_data: ForecastUpdate) -> Optional[Forecast]:
        """Updates metrics (like accuracy) of an existing forecast."""
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            logger.info(f"No metrics provided to update forecast {forecast_id}.")
            # Fetch and return existing? Or just return None?
            existing_response = await self.get_by_id(forecast_id)
            if existing_response and existing_response.data:
                return await self._instantiate_forecast(existing_response.data[0])
            return None

        try:
            updated_response = await self.update(forecast_id, update_dict)
            if updated_response and updated_response.data:
                 return await self._instantiate_forecast(updated_response.data[0])
            else:
                 logger.warning(f"Forecast {forecast_id} not found or update failed.")
                 return None
        except Exception as e:
             logger.error(f"Error updating forecast metrics for ID {forecast_id}: {e}")
             raise e

    # Delete might be needed for cleanup
    async def delete_forecast(self, forecast_id: int) -> bool:
        """Deletes a forecast record."""
        try:
            return await self.delete(forecast_id)
        except Exception as e:
             logger.error(f"Error deleting forecast {forecast_id}: {e}")
             return False 

    async def evaluate_forecast_accuracy(self, forecast_id: int) -> Optional[Forecast]:
        """
        Evaluates the accuracy of a forecast by comparing predicted demand with actual sales.
        Updates the forecast's model_metrics with MAE and RMSE.
        
        Args:
            forecast_id (int): ID of the forecast to evaluate
            
        Returns:
            Optional[Forecast]: Updated forecast if successful, None if not found
            
        Raises:
            ValueError: If forecast_id is invalid or data is insufficient
        """
        try:
            # Fetch the forecast
            forecast_response = await self.get_by_id(forecast_id)
            if not forecast_response or not forecast_response.data:
                logger.error(f"Forecast {forecast_id} not found")
                return None
                
            forecast = await self._instantiate_forecast(forecast_response.data[0])
            if not forecast:
                raise ValueError(f"Failed to instantiate forecast {forecast_id}")
                
            # Extract forecast period and predictions
            start_date = forecast.start_date
            end_date = forecast.end_date
            forecast_data = forecast.forecast_data.get('daily_predictions', [])
            if not forecast_data:
                raise ValueError(f"No daily predictions found in forecast {forecast_id}")
                
            # Get actual sales data for the forecast period
            days_diff = (end_date - start_date).days + 1
            sales_history = await self.product_service.get_historical_sales(
                product_id=forecast.product_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not sales_history:
                logger.warning(f"No actual sales data found for forecast {forecast_id}")
                return forecast
                
            # Prepare actual and predicted values
            actual_sales = pd.DataFrame(sales_history)
            actual_sales['date'] = pd.to_datetime(actual_sales['date'])
            actual_sales = actual_sales.set_index('date')['quantity']
            
            predicted_sales = pd.DataFrame(forecast_data)
            predicted_sales['ds'] = pd.to_datetime(predicted_sales['ds'])
            predicted_sales = predicted_sales.set_index('ds')['yhat']
            
            # Align dates and calculate metrics
            aligned_dates = actual_sales.index.intersection(predicted_sales.index)
            if len(aligned_dates) == 0:
                logger.warning(f"No matching dates found between predictions and actuals for forecast {forecast_id}")
                return forecast
                
            actuals = actual_sales[aligned_dates].values
            predictions = predicted_sales[aligned_dates].values
            
            # Calculate metrics
            mae = float(mean_absolute_error(actuals, predictions))
            rmse = float(np.sqrt(np.mean((actuals - predictions) ** 2)))
            
            # Update model metrics
            current_metrics = forecast.model_metrics or {}
            updated_metrics = {
                **current_metrics,
                "mae_actual": round(mae, 4),
                "rmse_actual": round(rmse, 4),
                "evaluation_date": datetime.utcnow().isoformat(),
                "evaluation_samples": len(aligned_dates),
                "total_actual_sales": int(sum(actuals)),
                "total_predicted_sales": int(sum(predictions)),
                "prediction_bias": float(round((sum(predictions) - sum(actuals)) / sum(actuals), 4))
            }
            
            # Update forecast in database
            update_data = {
                "model_metrics": updated_metrics,
                "accuracy": float(max(0, 1 - abs(updated_metrics["prediction_bias"])))  # Simple accuracy metric
            }
            
            updated_response = await self.update(forecast_id, update_data)
            if not updated_response or not updated_response.data:
                raise ValueError(f"Failed to update forecast {forecast_id} with accuracy metrics")
                
            updated_forecast = await self._instantiate_forecast(updated_response.data[0])
            logger.info(f"Successfully evaluated forecast {forecast_id} with MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            return updated_forecast
            
        except Exception as e:
            logger.error(f"Error evaluating forecast {forecast_id}: {e}")
            raise

    async def get_forecasts_by_product(
        self,
        product_id: int,
        period: Optional[str] = None
    ) -> List[Forecast]:
        """
        Retrieves all forecasts for a product across stores, optionally filtered by period.
        
        Args:
            product_id (int): ID of the product
            period (Optional[str]): Filter by period type (e.g., "30d", "60d")
            
        Returns:
            List[Forecast]: List of forecasts for the product
            
        Raises:
            ValueError: If product_id is invalid
        """
        try:
            # Verify product exists and get retailer_id for RLS
            product = await self.product_service.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
                
            # Build query
            query = self.client.table(self.table_name)\
                .select("*")\
                .eq("product_id", product_id)\
                .order("created_at", desc=True)
                
            # Add period filter if specified
            if period:
                query = query.eq("period_type", period)
                
            result = await query.execute()
            
            # Process results
            forecasts = []
            if result.data:
                for item_data in result.data:
                    forecast = await self._instantiate_forecast(item_data)
                    if forecast:
                        forecasts.append(forecast)
                        
            logger.info(f"Retrieved {len(forecasts)} forecasts for product {product_id}" + 
                       f" with period {period}" if period else "")
            return forecasts
            
        except Exception as e:
            logger.error(f"Error fetching forecasts for product {product_id}: {e}")
            raise 