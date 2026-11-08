from functools import lru_cache
from supabase import create_client, Client
from .config import settings

@lru_cache()
def get_supabase() -> Client:
    """
    Create and cache Supabase client instance
    Returns:
        Client: Supabase client instance
    """
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_KEY
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(url, key)

# Create a global instance
supabase: Client = get_supabase() 