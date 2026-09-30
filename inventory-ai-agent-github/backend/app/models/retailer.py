from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

class Retailer(BaseModel, Base):
    """Model for retail business owners"""
    __tablename__ = "retailers"

    # Basic Information
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    
    # Integration Settings
    shopify_store_url = Column(String(255))
    erp_system_type = Column(String(50))  # e.g., 'TOTVS', 'Datasystem'
    whatsapp_number = Column(String(20))
    
    # Relationships
    stores = relationship("Store", back_populates="retailer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Retailer {self.name}>" 