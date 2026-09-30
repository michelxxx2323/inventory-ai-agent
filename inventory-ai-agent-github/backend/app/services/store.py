from typing import List, Optional
from .base import BaseService
from ..models.store import Store

class StoreService(BaseService[Store]):
    """Service for store-specific operations"""
    
    def __init__(self):
        super().__init__("stores")
    
    async def get_by_retailer(self, retailer_id: int) -> List[Store]:
        """Get all stores for a specific retailer"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("retailer_id", retailer_id)\
            .execute()
        return result.data if result.data else []
    
    async def get_active_stores(self) -> List[Store]:
        """Get all active stores"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("is_active", True)\
            .execute()
        return result.data if result.data else []
    
    async def get_stores_with_inventory(self) -> List[Store]:
        """Get all stores with their current inventory"""
        result = self.client.table(self.table_name)\
            .select("*, inventories(*)")\
            .execute()
        return result.data if result.data else []
    
    async def deactivate(self, id: int) -> Optional[Store]:
        """Deactivate a store"""
        return await self.update(id, {"is_active": False})
    
    async def activate(self, id: int) -> Optional[Store]:
        """Activate a store"""
        return await self.update(id, {"is_active": True})
    
    async def get_by_location(self, latitude: float, longitude: float, radius_km: float) -> List[Store]:
        """Get stores within a radius of a location"""
        # Using Postgres's earthdistance extension through Supabase
        query = f"""
        SELECT *
        FROM {self.table_name}
        WHERE earth_distance(
            ll_to_earth({latitude}, {longitude}),
            ll_to_earth(latitude, longitude)
        ) <= {radius_km * 1000}
        """
        result = self.client.rpc("get_stores_by_location", {
            "p_latitude": latitude,
            "p_longitude": longitude,
            "p_radius_km": radius_km
        }).execute()
        return result.data if result.data else [] 