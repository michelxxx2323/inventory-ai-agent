from sqlalchemy import Column, Integer, Float, ForeignKey, String, JSON, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel, Base

class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class PurchaseOrder(BaseModel, Base):
    """Model for purchase orders"""
    __tablename__ = "purchase_orders"

    # Order Information
    order_number = Column(String(50), unique=True, nullable=False)
    status = Column(String, nullable=False, default=OrderStatus.DRAFT)
    
    # Dates
    order_date = Column(DateTime)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    
    # Order Details
    items = Column(JSON, nullable=False)  # List of {product_id, quantity, unit_price}
    total_amount = Column(Float, nullable=False)
    
    # AI Recommendations
    is_ai_recommended = Column(Boolean, default=False)
    recommendation_data = Column(JSON)  # AI reasoning and data points
    confidence_score = Column(Float)  # 0 to 1
    
    # Supplier Information
    supplier_name = Column(String(255))
    supplier_contact = Column(String(100))
    supplier_email = Column(String(255))
    
    # Foreign Keys
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    
    # Relationships
    store = relationship("Store", backref="purchase_orders")
    retailer = relationship("Retailer", backref="purchase_orders")
    
    def __repr__(self):
        return f"<PurchaseOrder {self.order_number} ({self.status})>" 