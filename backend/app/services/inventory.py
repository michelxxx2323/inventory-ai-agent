from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseService
from ..models.inventory import Inventory

class InventoryService(BaseService[Inventory]):
    """Service for inventory-specific operations"""
    
    def __init__(self):
        super().__init__("inventories")
    
    async def get_by_store(self, store_id: int) -> List[Inventory]:
        """Get all inventory items for a specific store"""
        result = self.client.table(self.table_name)\
            .select("*, products(*)")\
            .eq("store_id", store_id)\
            .execute()
        return result.data if result.data else []
    
    async def get_by_product(self, product_id: int) -> List[Inventory]:
        """Get inventory levels for a specific product across all stores"""
        result = self.client.table(self.table_name)\
            .select("*, stores(*)")\
            .eq("product_id", product_id)\
            .execute()
        return result.data if result.data else []
    
    async def update_quantity(
        self,
        id: int,
        new_quantity: int,
        reason: str,
        changed_by: Optional[str] = None
    ) -> Optional[Inventory]:
        """
        Update inventory quantity and log the change to history.
        
        Args:
            id: Inventory record ID
            new_quantity: New stock quantity (must be non-negative)
            reason: Reason for the quantity change
            changed_by: Optional user identifier (defaults to current auth user)
            
        Returns:
            Updated inventory record if successful, None otherwise
            
        Raises:
            ValueError: If id is invalid or new_quantity is negative
        """
        try:
            # Input validation
            if new_quantity < 0:
                raise ValueError("New quantity cannot be negative")
                
            # Get current inventory record with store data
            current = await self.get_by_id(id)
            if not current:
                raise ValueError(f"Invalid inventory id: {id}")
            
            old_quantity = current.get("current_stock", 0)
            
            # Prepare update data
            now = datetime.utcnow()
            update_data = {
                "current_stock": new_quantity,
                "last_updated": now,
                "update_reason": reason
            }
            
            # If available_stock is managed, update it too
            if "available_stock" in current:
                reserved = current.get("reserved_stock", 0)
                update_data["available_stock"] = max(0, new_quantity - reserved)
            
            # Update inventory record
            updated = await self.update(id, update_data)
            if not updated:
                raise ValueError("Failed to update inventory record")
            
            # Log the change to history
            # Note: We don't need to explicitly log if using the trigger,
            # but logging here provides a backup and more control
            await self.log_stock_change(
                inventory_id=id,
                old_stock=old_quantity,
                new_stock=new_quantity,
                reason=reason,
                changed_by=changed_by
            )
            
            return updated
            
        except ValueError as ve:
            print(f"Validation error in update_quantity: {str(ve)}")
            raise  # Re-raise validation errors for proper handling
        except Exception as e:
            print(f"Error updating quantity for inventory {id}: {str(e)}")
            return None
    
    async def get_low_stock(self, threshold: int = 10) -> List[Inventory]:
        """Get all inventory items below threshold"""
        result = self.client.table(self.table_name)\
            .select("*, products(*), stores(*)")\
            .lt("quantity", threshold)\
            .execute()
        return result.data if result.data else []
    
    async def get_inventory_changes(self, start_date: datetime, end_date: datetime) -> List[Inventory]:
        """Get inventory changes within a date range"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .gte("last_updated", start_date)\
            .lte("last_updated", end_date)\
            .order("last_updated", desc=True)\
            .execute()
        return result.data if result.data else []
    
    async def adjust_inventory(self, id: int, adjustment: int, reason: str) -> Optional[Inventory]:
        """Adjust inventory by relative amount (positive or negative)"""
        current = await self.get_by_id(id)
        if not current:
            return None
        new_quantity = current["quantity"] + adjustment
        return await self.update_quantity(id, new_quantity, reason)
    
    async def log_stock_change(
        self,
        inventory_id: int,
        old_stock: int,
        new_stock: int,
        reason: str,
        changed_by: Optional[str] = None
    ) -> bool:
        """
        Log a stock change to the inventory_history table.
        
        Args:
            inventory_id: ID of the inventory record
            old_stock: Previous stock level
            new_stock: New stock level
            reason: Reason for the change
            changed_by: User who made the change (defaults to current auth user)
            
        Returns:
            bool: True if logging was successful, False otherwise
            
        Raises:
            ValueError: If inventory_id is invalid or stock values are negative
        """
        try:
            # Validate inventory exists and get related IDs
            inventory = await self.get_by_id(inventory_id)
            if not inventory:
                raise ValueError(f"Invalid inventory_id: {inventory_id}")
            
            if old_stock < 0 or new_stock < 0:
                raise ValueError("Stock values cannot be negative")
            
            # Insert history record
            result = self.client.table("inventory_history").insert({
                "inventory_id": inventory_id,
                "product_id": inventory["product_id"],
                "store_id": inventory["store_id"],
                "retailer_id": inventory["store"]["retailer_id"],  # Assuming store relation is loaded
                "old_stock": old_stock,
                "new_stock": new_stock,
                "changed_by": changed_by or "system",  # Default to "system" if no user specified
                "reason": reason,
                "changed_at": datetime.utcnow().isoformat()
            }).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error logging stock change for inventory {inventory_id}: {str(e)}")
            return False
    
    async def get_stock_history(
        self,
        inventory_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stock change history for an inventory item with optional date filtering.
        
        Args:
            inventory_id: ID of the inventory record
            start_date: Optional start date for filtering records
            end_date: Optional end date for filtering records
            
        Returns:
            List of history records ordered by changed_at descending
            
        Raises:
            ValueError: If inventory_id is invalid
        """
        try:
            # Verify inventory exists
            inventory = await self.get_by_id(inventory_id)
            if not inventory:
                raise ValueError(f"Invalid inventory_id: {inventory_id}")
            
            # Build query
            query = self.client.table("inventory_history")\
                .select("*")\
                .eq("inventory_id", inventory_id)\
                .order("changed_at", desc=True)
            
            # Add date filters if provided
            if start_date:
                query = query.gte("changed_at", start_date.isoformat())
            if end_date:
                query = query.lte("changed_at", end_date.isoformat())
            
            # Execute query
            result = query.execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error fetching stock history for inventory {inventory_id}: {str(e)}")
            return [] 