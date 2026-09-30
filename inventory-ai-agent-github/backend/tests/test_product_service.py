# inventory ai agent/backend/tests/test_product_service.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Assuming your project structure allows this import path
# Adjust if necessary based on your project setup and PYTHONPATH
from app.services.product import ProductService
from app.schemas.product import ProductCreate, ProductUpdate
from app.models.product import Product # Needed for type checking/instance validation

# --- Test Fixtures ---

@pytest.fixture
def mock_supabase_client():
    """Mocks the Supabase client and its fluent API calls."""
    mock_client = MagicMock()

    # Mock the fluent interface methods (select, insert, update, delete, eq, etc.)
    # Each method should return the mock_client itself to allow chaining
    mock_client.table.return_value = mock_client
    mock_client.select.return_value = mock_client
    mock_client.insert.return_value = mock_client
    mock_client.update.return_value = mock_client
    mock_client.delete.return_value = mock_client
    mock_client.eq.return_value = mock_client
    mock_client.limit.return_value = mock_client
    mock_client.neq.return_value = mock_client # Add other filters as needed
    mock_client.gt.return_value = mock_client
    mock_client.lt.return_value = mock_client
    mock_client.or_.return_value = mock_client
    mock_client.rpc.return_value = mock_client

    # The final 'execute' method needs to be an AsyncMock
    mock_client.execute = AsyncMock()

    return mock_client

@pytest_asyncio.fixture
async def product_service(mock_supabase_client):
    """Provides an instance of ProductService with a mocked Supabase client."""
    # Patch the supabase client instance within the BaseService or wherever it's initialized
    # Adjust the patch target based on where 'supabase' is imported/used in BaseService
    with patch('app.services.base.supabase', mock_supabase_client):
        service = ProductService()
        # Ensure the service instance uses the mocked client
        service.client = mock_supabase_client
        yield service

# --- Sample Data ---

SAMPLE_RETAILER_ID = 1
SAMPLE_SKU = "TESTSKU123"
SAMPLE_PRODUCT_ID = 101
SAMPLE_STORE_ID = 5
NOW = datetime.utcnow()

# Sample product data dictionary returned from Supabase
SAMPLE_PRODUCT_DICT = {
    "id": SAMPLE_PRODUCT_ID,
    "retailer_id": SAMPLE_RETAILER_ID,
    "name": "Test Product",
    "sku": SAMPLE_SKU,
    "description": "A product for testing",
    "brand": "Tester",
    "category": "Testing",
    "subcategory": "Unit Tests",
    "base_price": 19.99,
    "current_price": 19.99,
    "cost_price": 10.00,
    "weight": 0.5,
    "dimensions": {"length": 10, "width": 5, "height": 2},
    "barcode": "123456789012",
    "is_active": True,
    "minimum_stock": 5,
    "maximum_stock": 50,
    "reorder_point": 10,
    "lead_time_days": 3,
    "shopify_product_id": "s123",
    "erp_product_id": "e456",
    "created_at": NOW,
    "updated_at": NOW,
}

# Sample ProductCreate schema data
SAMPLE_PRODUCT_CREATE_DATA = ProductCreate(
    name="New Test Product",
    sku="NEWTESTSKU",
    base_price=25.50,
    current_price=24.99,
    cost_price=12.00,
    # Include other required fields from ProductBase
    brand="NewBrand",
    category="NewCategory",
    is_active=True,
)

# Sample ProductUpdate schema data
SAMPLE_PRODUCT_UPDATE_DATA = ProductUpdate(
    current_price=18.99,
    is_active=False
)


# --- Test Cases ---

@pytest.mark.asyncio
async def test_get_by_sku_found(product_service: ProductService, mock_supabase_client):
    """Test get_by_sku when the product exists."""
    # Configure the mock execute() to return sample data
    mock_response = MagicMock()
    mock_response.data = [SAMPLE_PRODUCT_DICT]
    mock_supabase_client.execute.return_value = mock_response

    product = await product_service.get_by_sku(SAMPLE_RETAILER_ID, SAMPLE_SKU)

    # Assertions
    assert product is not None
    assert isinstance(product, Product)
    assert product.id == SAMPLE_PRODUCT_ID
    assert product.sku == SAMPLE_SKU
    assert product.retailer_id == SAMPLE_RETAILER_ID

    # Verify Supabase client calls
    mock_supabase_client.table.assert_called_with("products")
    mock_supabase_client.select.assert_called_with("*")
    mock_supabase_client.eq.assert_any_call("retailer_id", SAMPLE_RETAILER_ID)
    mock_supabase_client.eq.assert_any_call("sku", SAMPLE_SKU)
    mock_supabase_client.limit.assert_called_with(1)
    mock_supabase_client.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_by_sku_not_found(product_service: ProductService, mock_supabase_client):
    """Test get_by_sku when the product does not exist."""
    mock_response = MagicMock()
    mock_response.data = [] # Simulate no data returned
    mock_supabase_client.execute.return_value = mock_response

    product = await product_service.get_by_sku(SAMPLE_RETAILER_ID, "NONEXISTENT")

    assert product is None
    mock_supabase_client.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_or_update_product_create(product_service: ProductService, mock_supabase_client):
    """Test create_or_update_product when the product does not exist (creates new)."""
    # Mock get_by_sku response (product not found)
    mock_get_sku_response = MagicMock()
    mock_get_sku_response.data = []
    # Mock create response
    created_product_id = 999
    created_product_dict = {**SAMPLE_PRODUCT_CREATE_DATA.dict(), "id": created_product_id, "retailer_id": SAMPLE_RETAILER_ID, "created_at": NOW, "updated_at": NOW}
    mock_create_response = MagicMock()
    mock_create_response.data = [created_product_dict] # Supabase returns list

    # Set side effects for execute: first call (get_by_sku) returns empty, second call (create) returns new product
    mock_supabase_client.execute.side_effect = [mock_get_sku_response, mock_create_response]

    new_product = await product_service.create_or_update_product(SAMPLE_RETAILER_ID, SAMPLE_PRODUCT_CREATE_DATA)

    assert new_product is not None
    assert isinstance(new_product, Product)
    assert new_product.id == created_product_id
    assert new_product.sku == SAMPLE_PRODUCT_CREATE_DATA.sku
    assert new_product.retailer_id == SAMPLE_RETAILER_ID

    # Verify calls: select for get_by_sku, insert for create
    assert mock_supabase_client.execute.call_count == 2
    # Check insert call data
    expected_insert_data = SAMPLE_PRODUCT_CREATE_DATA.dict()
    expected_insert_data['retailer_id'] = SAMPLE_RETAILER_ID
    # The actual call to insert might be on the mock_client itself if table().insert() was mocked correctly
    # Find the insert call in the mock history if direct assertion fails
    # Example: find_call = next((c for c in mock_supabase_client.method_calls if c[0] == 'insert'), None)
    # assert find_call is not None
    # assert find_call[1][0] == expected_insert_data

@pytest.mark.asyncio
async def test_create_or_update_product_update(product_service: ProductService, mock_supabase_client):
    """Test create_or_update_product when the product exists (updates existing)."""
    # Mock get_by_sku response (product found)
    mock_get_sku_response = MagicMock()
    # Make sure the mock product dict has an 'id'
    mock_product_data = {**SAMPLE_PRODUCT_DICT, 'id': SAMPLE_PRODUCT_ID}
    mock_get_sku_response.data = [mock_product_data]
    # Mock update response
    updated_product_dict = {**mock_product_data, "current_price": 15.99, "updated_at": datetime.utcnow()}
    mock_update_response = MagicMock()
    mock_update_response.data = [updated_product_dict] # Supabase returns list

    # Set side effects for execute: first call (get_by_sku), second call (update)
    mock_supabase_client.execute.side_effect = [mock_get_sku_response, mock_update_response]

    # Create data that would trigger an update (matches existing SKU)
    update_trigger_data = ProductCreate( # Use ProductCreate as input type
        sku=SAMPLE_SKU, # Match existing SKU
        name=mock_product_data["name"], # Keep some fields same
        base_price=mock_product_data["base_price"],
        current_price=15.99, # Change a field
        cost_price=mock_product_data["cost_price"],
         # Include other required fields
        brand=mock_product_data["brand"],
        category=mock_product_data["category"],
        is_active=mock_product_data["is_active"],
    )

    updated_product = await product_service.create_or_update_product(SAMPLE_RETAILER_ID, update_trigger_data)

    assert updated_product is not None
    assert isinstance(updated_product, Product)
    assert updated_product.id == SAMPLE_PRODUCT_ID
    assert updated_product.sku == SAMPLE_SKU
    assert updated_product.current_price == 15.99 # Check updated value

    # Verify calls: select for get_by_sku, update for update
    assert mock_supabase_client.execute.call_count == 2
    # Check update call data and filter
    # Example: update_call = next((c for c in mock_supabase_client.method_calls if c[0] == 'update'), None)
    # assert update_call is not None
    # update_payload = update_call[1][0]
    # assert update_payload['current_price'] == 15.99
    # eq_call = next((c for c in mock_supabase_client.method_calls if c[0] == 'eq' and c[1][0] == 'id'), None)
    # assert eq_call[1][1] == SAMPLE_PRODUCT_ID


@pytest.mark.asyncio
async def test_get_products_by_store(product_service: ProductService, mock_supabase_client):
    """Test retrieving products associated with a specific store."""
    # Mock response: products linked to the store via inventories table
    product1_store_dict = {**SAMPLE_PRODUCT_DICT, "id": 101, "inventories": {"store_id": SAMPLE_STORE_ID, "quantity": 10}}
    product2_store_dict = {**SAMPLE_PRODUCT_DICT, "id": 102, "sku": "OTHER SKU", "inventories": {"store_id": SAMPLE_STORE_ID, "quantity": 5}}
    mock_response = MagicMock()
    mock_response.data = [product1_store_dict, product2_store_dict]
    mock_supabase_client.execute.return_value = mock_response

    products = await product_service.get_products_by_store(SAMPLE_STORE_ID)

    assert products is not None
    assert len(products) == 2
    assert all(isinstance(p, Product) for p in products)
    assert products[0].id == 101
    assert products[1].id == 102

    # Verify Supabase client calls
    mock_supabase_client.table.assert_called_with("products")
    mock_supabase_client.select.assert_called_with("*, inventories!inner(*)")
    mock_supabase_client.eq.assert_called_with("inventories.store_id", SAMPLE_STORE_ID)
    mock_supabase_client.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_product(product_service: ProductService, mock_supabase_client):
    """Test the explicit update_product method."""
    updated_data_dict = {**SAMPLE_PRODUCT_DICT, "current_price": SAMPLE_PRODUCT_UPDATE_DATA.current_price, "is_active": SAMPLE_PRODUCT_UPDATE_DATA.is_active}
    mock_response = MagicMock()
    mock_response.data = [updated_data_dict]
    mock_supabase_client.execute.return_value = mock_response

    updated_product = await product_service.update_product(SAMPLE_PRODUCT_ID, SAMPLE_PRODUCT_UPDATE_DATA)

    assert updated_product is not None
    assert isinstance(updated_product, Product)
    assert updated_product.id == SAMPLE_PRODUCT_ID
    assert updated_product.current_price == SAMPLE_PRODUCT_UPDATE_DATA.current_price
    assert updated_product.is_active == SAMPLE_PRODUCT_UPDATE_DATA.is_active

    # Verify Supabase client calls
    mock_supabase_client.table.assert_called_with("products")
    # Check that update payload contains only the updated fields
    expected_update_payload = SAMPLE_PRODUCT_UPDATE_DATA.dict(exclude_unset=True)
    # update() should be called with expected_update_payload
    # eq() should be called with 'id', SAMPLE_PRODUCT_ID
    mock_supabase_client.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_product(product_service: ProductService, mock_supabase_client):
    """Test the explicit delete_product method."""
    # Mock response indicates success (usually non-empty data or specific flag)
    mock_response = MagicMock()
    # Supabase delete returns the deleted records
    mock_response.data = [SAMPLE_PRODUCT_DICT] 
    mock_supabase_client.execute.return_value = mock_response

    # Assuming BaseService delete returns True if response.data is truthy
    deleted = await product_service.delete_product(SAMPLE_PRODUCT_ID)

    assert deleted is True

    # Verify Supabase client calls
    mock_supabase_client.table.assert_called_with("products")
    mock_supabase_client.delete.assert_called_once()
    mock_supabase_client.eq.assert_called_with("id", SAMPLE_PRODUCT_ID)
    mock_supabase_client.execute.assert_called_once()

@pytest.mark.asyncio
async def test_delete_product_not_found(product_service: ProductService, mock_supabase_client):
    """Test deleting a product that doesnt exist."""
    # Mock response indicates failure (empty data)
    mock_response = MagicMock()
    mock_response.data = [] 
    mock_supabase_client.execute.return_value = mock_response

    deleted = await product_service.delete_product(9999) # Non-existent ID

    # Assuming BaseService delete returns False if response.data is falsy
    assert deleted is False

    # Verify Supabase client calls
    mock_supabase_client.execute.assert_called_once()


# Add more tests for edge cases, error handling, other methods (e.g., list_top_sellers)
# Consider testing validation errors if invalid data is passed 