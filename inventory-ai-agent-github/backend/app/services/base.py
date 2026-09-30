from typing import Any, Dict, List, Optional, TypeVar, Generic
from ..core.database import supabase

T = TypeVar('T')

class BaseService(Generic[T]):
    """Base service class for database operations"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.client = supabase
    
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new record"""
        result = self.client.table(self.table_name).insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get a record by ID"""
        result = self.client.table(self.table_name).select("*").eq("id", id).execute()
        return result.data[0] if result.data else None
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination"""
        result = self.client.table(self.table_name).select("*").range(offset, offset + limit - 1).execute()
        return result.data if result.data else []
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update a record"""
        result = self.client.table(self.table_name).update(data).eq("id", id).execute()
        return result.data[0] if result.data else None
    
    async def delete(self, id: int) -> bool:
        """Delete a record"""
        result = self.client.table(self.table_name).delete().eq("id", id).execute()
        return bool(result.data)
    
    async def count(self) -> int:
        """Count total records"""
        result = self.client.table(self.table_name).select("id", count="exact").execute()
        return result.count if hasattr(result, 'count') else 0 