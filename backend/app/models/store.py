from sqlalchemy import Column, String, ForeignKey, Boolean, Float, Integer
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

class Store(BaseModel, Base):
    """Model for individual retail store locations"""
    __tablename__ = "stores"

    # Basic Information
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    country = Column(String(50), nullable=False)
    postal_code = Column(String(20), nullable=False)
    
    # Contact Information
    manager_name = Column(String(100))
    manager_email = Column(String(255))
    manager_phone = Column(String(20))
    whatsapp_number = Column(String(20))
    
    # Store Details
    is_active = Column(Boolean, default=True)
    store_size = Column(Float)  # in square meters/feet
    storage_capacity = Column(Float)  # in cubic meters/feet
    
    # Foreign Keys
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    
    # Relationships
    retailer = relationship("Retailer", back_populates="stores")
    inventories = relationship("Inventory", back_populates="store", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Store {self.name} - {self.city}>" 