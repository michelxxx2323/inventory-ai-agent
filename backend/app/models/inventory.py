from sqlalchemy import Column, Integer, Float, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

class Inventory(BaseModel, Base):
    """Model for tracking product inventory levels at each store"""
    __tablename__ = "inventories"

    # Stock Information
    current_stock = Column(Integer, nullable=False, default=0)
    available_stock = Column(Integer, nullable=False, default=0)  # current_stock - reserved
    reserved_stock = Column(Integer, nullable=False, default=0)  # items in shopping carts/pending orders
    
    # Location Information
    storage_location = Column(String(50))  # e.g., "Shelf A1", "Warehouse B"
    
    # Stock History
    stock_history = Column(JSON)  # List of historical stock levels with timestamps
    
    # Sales Metrics
    daily_sales_velocity = Column(Float, default=0.0)  # Average daily sales
    weekly_sales_velocity = Column(Float, default=0.0)  # Average weekly sales
    monthly_sales_velocity = Column(Float, default=0.0)  # Average monthly sales
    
    # Foreign Keys
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="inventories")
    store = relationship("Store", back_populates="inventories")
    
    class Config:
        unique_together = (("product_id", "store_id"),)
    
    def __repr__(self):
        return f"<Inventory {self.product_id} at Store {self.store_id}>" 