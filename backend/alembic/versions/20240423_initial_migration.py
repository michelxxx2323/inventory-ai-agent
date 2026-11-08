"""Initial migration

Revision ID: 20240423_0001
Create Date: 2024-04-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240423_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create retailers table
    op.create_table(
        'retailers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('shopify_store_url', sa.String(length=255), nullable=True),
        sa.Column('erp_system_type', sa.String(length=50), nullable=True),
        sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_retailers_email'), 'retailers', ['email'], unique=True)

    # Create stores table
    op.create_table(
        'stores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('country', sa.String(length=50), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('manager_name', sa.String(length=100), nullable=True),
        sa.Column('manager_email', sa.String(length=255), nullable=True),
        sa.Column('manager_phone', sa.String(length=20), nullable=True),
        sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('store_size', sa.Float(), nullable=True),
        sa.Column('storage_capacity', sa.Float(), nullable=True),
        sa.Column('retailer_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['retailer_id'], ['retailers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('base_price', sa.Float(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('cost_price', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('dimensions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('minimum_stock', sa.Integer(), nullable=True),
        sa.Column('maximum_stock', sa.Integer(), nullable=True),
        sa.Column('reorder_point', sa.Integer(), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('shopify_product_id', sa.String(length=100), nullable=True),
        sa.Column('erp_product_id', sa.String(length=100), nullable=True),
        sa.Column('retailer_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['retailer_id'], ['retailers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)

    # Create inventories table
    op.create_table(
        'inventories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('available_stock', sa.Integer(), nullable=False),
        sa.Column('reserved_stock', sa.Integer(), nullable=False),
        sa.Column('storage_location', sa.String(length=50), nullable=True),
        sa.Column('stock_history', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('daily_sales_velocity', sa.Float(), nullable=True),
        sa.Column('weekly_sales_velocity', sa.Float(), nullable=True),
        sa.Column('monthly_sales_velocity', sa.Float(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'store_id', name='uq_inventory_product_store')
    )

    # Create forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('predicted_demand', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('forecast_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recommended_stock', sa.Integer(), nullable=False),
        sa.Column('recommended_actions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('model_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('mape', sa.Float(), nullable=True),
        sa.Column('rmse', sa.Float(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create purchase_orders table
    op.create_table(
        'purchase_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('order_date', sa.DateTime(), nullable=True),
        sa.Column('expected_delivery_date', sa.DateTime(), nullable=True),
        sa.Column('actual_delivery_date', sa.DateTime(), nullable=True),
        sa.Column('items', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('is_ai_recommended', sa.Boolean(), nullable=True),
        sa.Column('recommendation_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('supplier_name', sa.String(length=255), nullable=True),
        sa.Column('supplier_contact', sa.String(length=100), nullable=True),
        sa.Column('supplier_email', sa.String(length=255), nullable=True),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('retailer_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['retailer_id'], ['retailers.id'], ),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_number')
    )

def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('purchase_orders')
    op.drop_table('forecasts')
    op.drop_table('inventories')
    op.drop_table('products')
    op.drop_table('stores')
    op.drop_table('retailers') 