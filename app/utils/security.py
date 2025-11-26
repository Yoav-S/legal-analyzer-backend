"""
Security utilities for authentication and authorization.
"""
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.config import settings
from app.utils.errors import AuthenticationError


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token from Supabase.
    
    This function verifies the JWT token locally using the Supabase JWT secret.
    No external API calls are made - verification happens on the backend.
    
    Args:
        token: JWT token string (with or without 'Bearer ' prefix)
        
    Returns:
        Decoded token payload containing:
        - sub: User ID (Supabase UUID)
        - email: User email
        - role: User role (typically "authenticated")
        - exp: Token expiration timestamp
        
    Raises:
        AuthenticationError: If token is invalid, expired, or missing
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        if not token:
            raise AuthenticationError("Token is empty")
        
        # Decode and verify token (Supabase uses HS256)
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token string (with or without 'Bearer ' prefix)
        
    Returns:
        User ID (Supabase UUID from 'sub' claim)
        
    Raises:
        AuthenticationError: If token is invalid or missing user ID
    """
    payload = decode_jwt_token(token)
    user_id = payload.get("sub") or payload.get("user_id")
    
    if not user_id:
        raise AuthenticationError("Token missing user ID")
    
    return user_id


def get_token_payload(token: str) -> Dict[str, Any]:
    """
    Get full token payload with all claims.
    
    This is a convenience function that returns the complete decoded token payload.
    
    Args:
        token: JWT token string (with or without 'Bearer ' prefix)
        
    Returns:
        Complete token payload dictionary with all claims
    """
    return decode_jwt_token(token)


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

