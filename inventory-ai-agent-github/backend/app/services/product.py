from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from .base import BaseService
from ..models.product import Product
from ..schemas.product import ProductCreate, ProductUpdate
from sqlalchemy import func, cast, Date as SQLDate
import logging

logger = logging.getLogger(__name__)

class ProductService(BaseService[Product]):
    """Service for product-specific operations"""
    
    def __init__(self):
        super().__init__("products")
    
    async def get_by_retailer(self, retailer_id: int) -> List[Product]:
        """Get all products for a specific retailer"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("retailer_id", retailer_id)\
            .execute()
        return result.data if result.data else []
    
    async def get_by_category(self, category: str) -> List[Product]:
        """Get all products in a specific category"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("category", category)\
            .execute()
        return result.data if result.data else []
    
    async def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """Get products with stock below threshold across all stores"""
        result = self.client.table(self.table_name)\
            .select("*, inventories!inner(*)")\
            .lt("inventories.quantity", threshold)\
            .execute()
        return result.data if result.data else []
    
    async def search_products(self, query: str) -> List[Product]:
        """Search products by name or description"""
        result = self.client.table(self.table_name)\
            .select("*")\
            .or_(f"name.ilike.%{query}%,description.ilike.%{query}%")\
            .execute()
        return result.data if result.data else []
    
    async def get_products_with_inventory(self) -> List[Product]:
        """Get all products with their current inventory levels"""
        result = self.client.table(self.table_name)\
            .select("*, inventories(*)")\
            .execute()
        return result.data if result.data else []
    
    async def update_price(self, id: int, new_price: float, reason: str) -> Optional[Product]:
        """
        Update product price with audit trail
        Args:
            id: Product ID
            new_price: New price value
            reason: Reason for price change
        """
        now = datetime.utcnow()
        data = {
            "price": new_price,
            "price_updated_at": now,
            "price_update_reason": reason,
            "last_price_change": now
        }
        return await self.update(id, data)
    
    async def get_by_sku(self, retailer_id: int, sku: str) -> Optional[Product]:
        """
        Get product by SKU for a specific retailer
        Args:
            retailer_id: ID of the retailer (int)
            sku: Product SKU (Stock Keeping Unit)
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("retailer_id", retailer_id)\
            .eq("sku", sku)\
            .limit(1)\
            .execute()
        if result.data:
            try:
                return Product(**result.data[0])
            except TypeError as e:
                print(f"Error instantiating Product model: {e}, data: {result.data[0]}")
                return None
        else:
            return None
    
    async def create_or_update_product(self, retailer_id: int, data: ProductCreate) -> Optional[Product]:
        """
        Synchronize products from external sources like Shopify/ERP.
        Creates a new product if it doesn't exist for the retailer based on SKU,
        otherwise updates the existing one.
        Args:
            retailer_id: The ID of the retailer (int).
            data: Product data for creation or update (ProductCreate schema).
        Returns:
            The created or updated product (as Product model instance) or None if failed.
        """
        existing = await self.get_by_sku(retailer_id, data.sku)
        if existing:
            if not hasattr(existing, 'id') or not existing.id:
                print(f"Error: Existing product found for SKU {data.sku} and retailer {retailer_id} but missing a valid ID.")
                raise ValueError("Existing product found but missing ID.")

            update_model = ProductUpdate(**data.dict())
            update_data_dict = update_model.dict(exclude_unset=True)

            if not update_data_dict:
                return existing

            updated_product_data = await self.update(existing.id, update_data_dict)

            if updated_product_data:
                try:
                    return Product(**updated_product_data[0])
                except (TypeError, IndexError, AttributeError) as e:
                    print(f"Error instantiating Product after update: {e}, data: {updated_product_data}")
                    return None
            else:
                print(f"Failed to update product ID {existing.id}")
                return None
        else:
            create_data_dict = data.dict()
            create_data_dict['retailer_id'] = retailer_id
            created_product_data = await self.create(create_data_dict)

            if created_product_data:
                try:
                    return Product(**created_product_data[0])
                except (TypeError, IndexError, AttributeError) as e:
                    print(f"Error instantiating Product after create: {e}, data: {created_product_data}")
                    return None
            else:
                print(f"Failed to create product for SKU {data.sku}, retailer {retailer_id}")
                return None
    
    async def list_top_sellers(self, limit: int = 10, days: int = 30) -> List[Product]:
        """
        Get top selling products based on sales quantity
        Args:
            limit: Number of products to return
            days: Number of days to look back
        """
        query = f"""
        WITH sales_data AS (
            SELECT 
                product_id,
                SUM(quantity_change) as total_sales
            FROM inventory_changes
            WHERE 
                change_type = 'sale'
                AND created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY product_id
            ORDER BY total_sales DESC
            LIMIT {limit}
        )
        SELECT p.*, sd.total_sales
        FROM {self.table_name} p
        INNER JOIN sales_data sd ON p.id = sd.product_id
        ORDER BY sd.total_sales DESC
        """
        
        result = self.client.rpc('get_top_selling_products', {
            'p_days': days,
            'p_limit': limit
        }).execute()
        
        return result.data if result.data else []
    
    async def get_products_by_store(self, store_id: int) -> List[Product]:
        """Get all products available in a specific store"""
        try:
            result = self.client.table(self.table_name)\
                .select("*, inventories!inner(*)")\
                .eq("inventories.store_id", store_id)\
                .execute()

            products = []
            if result.data:
                for p_data in result.data:
                    inventory_data = p_data.pop('inventories', None)
                    try:
                        product = Product(**p_data)
                        products.append(product)
                    except TypeError as e:
                        print(f"Error instantiating Product in get_products_by_store: {e}, data: {p_data}")
            return products
        except Exception as e:
            print(f"Error fetching products for store {store_id}: {e}")
            return []
    
    async def create_product(self, retailer_id: int, product_data: ProductCreate) -> Optional[Product]:
        """Explicitly create a product using the ProductCreate schema."""
        create_dict = product_data.dict()
        create_dict['retailer_id'] = retailer_id
        try:
            created_data = await self.create(create_dict)
            if created_data:
                return Product(**created_data[0])
            else:
                print(f"Failed to create product (create returned None) for retailer {retailer_id}, data: {product_data.sku}")
                return None
        except Exception as e:
            print(f"Error during explicit product creation: {e}")
            return None
    
    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Explicitly update a product using the ProductUpdate schema."""
        update_dict = product_data.dict(exclude_unset=True)
        if not update_dict:
            print(f"No fields to update for product {product_id}")
            try:
                existing_data = await self.get_by_id(product_id)
                return Product(**existing_data[0]) if existing_data else None
            except Exception as e:
                print(f"Error fetching existing product {product_id} during empty update: {e}")
                return None

        try:
            updated_data = await self.update(product_id, update_dict)
            if updated_data:
                return Product(**updated_data[0])
            else:
                print(f"Failed to update product {product_id} (update returned None)")
                return None
        except Exception as e:
            print(f"Error during explicit product update for ID {product_id}: {e}")
            return None
    
    async def delete_product(self, product_id: int) -> bool:
        """Delete a product by its ID."""
        try:
            return await self.delete(product_id)
        except Exception as e:
            print(f"Error deleting product {product_id}: {e}")
            return False
    
    async def get_historical_sales(self, product_id: int, days_history: int = 365) -> List[Dict[str, Any]]:
        """
        Fetches aggregated daily sales quantity for a product over a specified history period.

        Args:
            product_id: The ID of the product.
            days_history: Number of past days to fetch sales data for.

        Returns:
            List of dictionaries, e.g., [{'date': 'YYYY-MM-DD', 'quantity': 2}, ...]
            Returns empty list if no sales data found.
        """
        if days_history <= 0:
            return []

        # Calculate the start date for the history period
        start_date = date.today() - timedelta(days=days_history)
        logger.info(f"Fetching historical sales for product {product_id} from {start_date}")

        try:
            # ---- Using RPC function (Recommended approach) ----
            # Assume an SQL function `get_daily_sales(p_product_id INT, p_start_date DATE)` exists
            rpc_params = {
                'p_product_id': product_id,
                'p_start_date': start_date.isoformat()
            }
            result = await self.client.rpc('get_daily_sales', rpc_params).execute()

            if result.data:
                 # Convert date objects/strings to 'YYYY-MM-DD' strings if needed
                 # RPC function should return date as 'YYYY-MM-DD' string or date object
                 return [{'date': item['sale_date'], 'quantity': item['total_quantity']} for item in result.data]
            else:
                logger.warning(f"No historical sales data found for product {product_id} after {start_date}")
                return []

        except Exception as e:
            logger.error(f"Error fetching historical sales for product {product_id}: {e}")
            # Depending on Supabase client errors, check if RPC function exists
            if hasattr(e, 'message') and "function public.get_daily_sales(p_product_id => integer, p_start_date => text) does not exist" in e.message:
                 logger.error("RPC function 'get_daily_sales(integer, text)' not found in database. Please create it with the correct signature.")
                 # You might need to adjust the signature based on the actual error message
            elif "relation \"inventory_changes\" does not exist" in str(e):
                 logger.error("Table 'inventory_changes' not found, cannot fetch sales history.")
            # Re-raise the exception or return empty list
            raise e # Or return [] 