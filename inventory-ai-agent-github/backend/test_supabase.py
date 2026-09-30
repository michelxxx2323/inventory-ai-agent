import asyncio
from supabase import create_client

import os

# Supabase credentials come from environment variables (see backend/.env.example)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

EXPECTED_TABLES = [
    'retailers',
    'stores',
    'products',
    'inventories',
    'forecasts',
    'purchase_orders'
]

async def verify_tables():
    try:
        print("\nConnecting to Supabase...")
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print("\nChecking tables existence...")
        
        for table in EXPECTED_TABLES:
            try:
                # Try to select from each table
                result = await client.from_(table).select('*').limit(0).execute()
                print(f"✅ Table '{table}' exists")
                
                # For forecasts table, show its structure
                if table == 'forecasts':
                    print(f"\nColumns in '{table}' table:")
                    for col in result.columns:
                        print(f"  ✓ {col}")
                    
            except Exception as table_error:
                print(f"❌ Table '{table}' not found or error: {str(table_error)}")
        
    except Exception as e:
        print(f"\n❌ Error checking tables: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(verify_tables())
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        exit(1) 