from typing import List, Optional
from .base import BaseService
from ..models.retailer import Retailer

class RetailerService(BaseService[Retailer]):
    """Service for retailer-specific operations"""
    
    def __init__(self):
        super().__init__("retailers")
    
    async def get_by_email(self, email: str) -> Optional[Retailer]:
        """Get a retailer by email"""
        result = self.client.table(self.table_name).select("*").eq("email", email).execute()
        return result.data[0] if result.data else None
    
    async def get_active_retailers(self) -> List[Retailer]:
        """Get all active retailers"""
        result = self.client.table(self.table_name).select("*").eq("is_active", True).execute()
        return result.data if result.data else []
    
    async def get_retailers_with_stores(self) -> List[Retailer]:
        """Get all retailers with their stores"""
        result = self.client.table(self.table_name)\
            .select("*, stores(*)")\
            .execute()
        return result.data if result.data else []
    
    async def deactivate(self, id: int) -> Optional[Retailer]:
        """Deactivate a retailer"""
        return await self.update(id, {"is_active": False})
    
    async def activate(self, id: int) -> Optional[Retailer]:
        """Activate a retailer"""
        return await self.update(id, {"is_active": True}) 