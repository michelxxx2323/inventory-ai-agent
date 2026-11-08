from sqlalchemy import Column, String, Float, Boolean, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

class Product(BaseModel, Base):
    """Model for products in inventory"""
    __tablename__ = "products"

    # Basic Information
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(1000))
    brand = Column(String(100))
    category = Column(String(100))
    subcategory = Column(String(100))
    
    # Pricing
    base_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    
    # Product Details
    weight = Column(Float)  # in kg
    dimensions = Column(JSON)  # {length, width, height} in cm
    barcode = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    # Stock Management
    minimum_stock = Column(Integer, default=0)
    maximum_stock = Column(Integer, default=1000)
    reorder_point = Column(Integer, default=10)
    lead_time_days = Column(Integer, default=7)  # average days to restock
    
    # External References
    shopify_product_id = Column(String(100))
    erp_product_id = Column(String(100))
    
    # Foreign Keys
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    
    # Relationships
    retailer = relationship("Retailer", backref="products")
    inventories = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product {self.sku} - {self.name}>" 