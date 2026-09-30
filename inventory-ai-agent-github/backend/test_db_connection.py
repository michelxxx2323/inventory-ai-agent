from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_connection():
    try:
        # Get database URL from environment variable
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
            
        print("\nTesting database connection...")
        print(f"Database URL: {database_url.replace(database_url.split('@')[0], 'postgresql://****:****')}")
        
        # Create engine and test connection
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute("SELECT version();").fetchone()
            
        print("\n✅ Successfully connected to the database!")
        print(f"PostgreSQL version: {result[0]}")
        return True
        
    except SQLAlchemyError as e:
        print("\n❌ Failed to connect to the database!")
        print(f"Error: {str(e)}")
        return False
    except Exception as e:
        print("\n❌ An unexpected error occurred!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if not success:
        print("\nPlease check your .env file and make sure DATABASE_URL is set correctly")
        exit(1) 