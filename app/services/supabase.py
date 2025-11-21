"""
Supabase authentication service.
"""
import httpx
from typing import Optional, Dict, Any

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SupabaseService:
    """Service for interacting with Supabase Auth API."""
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.anon_key = settings.SUPABASE_ANON_KEY
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user from Supabase Auth.
        
        Args:
            user_id: Supabase user UUID
            
        Returns:
            User data or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/auth/v1/admin/users/{user_id}",
                    headers={
                        "apikey": self.service_role_key,
                        "Authorization": f"Bearer {self.service_role_key}",
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get user from Supabase: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching user from Supabase: {e}")
            return None
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token with Supabase.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload or None if invalid
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/auth/v1/user",
                    headers={
                        "apikey": self.anon_key,
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error verifying token with Supabase: {e}")
            return None

