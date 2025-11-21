"""
Security utilities for authentication and authorization.
"""
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.config import settings
from app.utils.errors import AuthenticationError


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token from Supabase.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Decode token (Supabase uses HS256)
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            options={"verify_signature": True},
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID (Supabase UUID)
    """
    payload = decode_jwt_token(token)
    user_id = payload.get("sub") or payload.get("user_id")
    
    if not user_id:
        raise AuthenticationError("Token missing user ID")
    
    return user_id


def validate_file_type(filename: str) -> bool:
    """
    Validate file extension is allowed.
    
    Args:
        filename: File name with extension
        
    Returns:
        True if allowed, False otherwise
    """
    if not filename:
        return False
    
    extension = filename.split(".")[-1].lower()
    return extension in settings.allowed_file_extensions


def validate_file_size(file_size: int) -> bool:
    """
    Validate file size is within limits.
    
    Args:
        file_size: File size in bytes
        
    Returns:
        True if within limits, False otherwise
    """
    return file_size <= settings.max_file_size_bytes

