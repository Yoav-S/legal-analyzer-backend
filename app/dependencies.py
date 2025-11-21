"""
FastAPI dependency injection for common dependencies.
"""
from fastapi import Depends, HTTPException, Header
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.utils.errors import AuthenticationError
from app.utils.security import get_user_id_from_token
from app.models.user import User
from app.services.supabase import SupabaseService

# MongoDB connection (singleton)
_mongodb_client: Optional[AsyncIOMotorClient] = None
_mongodb_db: Optional[AsyncIOMotorDatabase] = None


def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client (singleton)."""
    global _mongodb_client
    
    if _mongodb_client is None:
        _mongodb_client = AsyncIOMotorClient(settings.mongodb_connection_string)
    
    return _mongodb_client


def get_mongodb_db() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    global _mongodb_db
    
    if _mongodb_db is None:
        client = get_mongodb_client()
        _mongodb_db = client[settings.MONGODB_DB_NAME]
    
    return _mongodb_db


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Extract and verify user ID from JWT token in Authorization header.
    
    Args:
        authorization: Authorization header value (Bearer token)
        
    Returns:
        User ID (Supabase UUID)
        
    Raises:
        AuthenticationError: If token is missing or invalid
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")
    
    try:
        user_id = get_user_id_from_token(authorization)
        return user_id
    except Exception as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
) -> User:
    """
    Get current authenticated user from database.
    
    Args:
        user_id: User ID from JWT token
        db: MongoDB database instance
        
    Returns:
        User model instance
        
    Raises:
        NotFoundError: If user doesn't exist
    """
    from app.models.user import User
    
    user = await User.get_by_id(db, user_id)
    if not user:
        raise AuthenticationError("User not found")
    
    return user


def get_supabase_service() -> SupabaseService:
    """Get Supabase service instance."""
    return SupabaseService()

