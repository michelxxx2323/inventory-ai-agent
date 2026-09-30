-- Add price audit fields to products table
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS price_updated_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS price_update_reason TEXT,
    ADD COLUMN IF NOT EXISTS last_price_change TIMESTAMP WITH TIME ZONE;

-- Create price history table for complete audit trail
CREATE TABLE IF NOT EXISTS product_price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT
);

-- Create index for faster queries on product price history
CREATE INDEX IF NOT EXISTS idx_product_price_history_product_id 
    ON product_price_history(product_id);

-- Create function to automatically track price changes
CREATE OR REPLACE FUNCTION track_product_price_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.price IS DISTINCT FROM NEW.price THEN
        INSERT INTO product_price_history (
            product_id,
            old_price,
            new_price,
            reason,
            created_at,
            created_by
        ) VALUES (
            NEW.id,
            OLD.price,
            NEW.price,
            NEW.price_update_reason,
            NEW.price_updated_at,
            current_user
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for price change tracking
DROP TRIGGER IF EXISTS product_price_change_trigger ON products;
CREATE TRIGGER product_price_change_trigger
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION track_product_price_changes();

-- Add RLS (Row Level Security) policies
ALTER TABLE product_price_history ENABLE ROW LEVEL SECURITY;

-- Create policy for viewing price history
CREATE POLICY view_price_history ON product_price_history
    FOR SELECT
    USING (
        -- Allow users to view price history if they have access to the product
        EXISTS (
            SELECT 1 FROM products p
            WHERE p.id = product_price_history.product_id
            AND (
                p.retailer_id IN (
                    SELECT retailer_id FROM user_retailers
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

-- Create policy for inserting price history
CREATE POLICY insert_price_history ON product_price_history
    FOR INSERT
    WITH CHECK (
        -- Allow users to insert price history if they have access to the product
        EXISTS (
            SELECT 1 FROM products p
            WHERE p.id = product_price_history.product_id
            AND (
                p.retailer_id IN (
                    SELECT retailer_id FROM user_retailers
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

-- Add comments for documentation
COMMENT ON TABLE product_price_history IS 'Tracks all price changes for products';
COMMENT ON COLUMN product_price_history.old_price IS 'Previous price before the change';
COMMENT ON COLUMN product_price_history.new_price IS 'New price after the change';
COMMENT ON COLUMN product_price_history.reason IS 'Reason for the price change';
COMMENT ON COLUMN product_price_history.created_by IS 'User who made the price change'; 