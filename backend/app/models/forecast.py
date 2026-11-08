from sqlalchemy import Column, Integer, Float, ForeignKey, String, JSON, Date
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

class Forecast(BaseModel, Base):
    """Model for demand forecasts"""
    __tablename__ = "forecasts"

    # Forecast Period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # '30_days', '60_days', '90_days'
    
    # Forecast Data
    predicted_demand = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0 to 1
    forecast_data = Column(JSON)  # Detailed forecast data points
    
    # Recommendations
    recommended_stock = Column(Integer, nullable=False)
    recommended_actions = Column(JSON)  # List of suggested actions
    
    # Model Information
    model_version = Column(String(50))  # Version of the ML model used
    model_parameters = Column(JSON)  # Parameters used for this forecast
    
    # Performance Metrics
    accuracy = Column(Float)  # Accuracy of previous forecast
    mape = Column(Float)  # Mean Absolute Percentage Error
    rmse = Column(Float)  # Root Mean Square Error
    
    # Foreign Keys
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="forecasts")
    store = relationship("Store", backref="forecasts")
    
    def __repr__(self):
        return f"<Forecast {self.product_id} ({self.period_type})>" 