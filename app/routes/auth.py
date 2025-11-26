"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, Header
from typing import Optional

from app.dependencies import get_current_user, get_current_user_id
from app.models.user import User
from app.utils.errors import AuthenticationError
from app.utils.security import decode_jwt_token

router = APIRouter()


@router.post("/verify-token")
async def verify_token(
    authorization: Optional[str] = Header(None),
):
    """
    Verify Supabase JWT token locally.
    
    This endpoint verifies the JWT token on the backend without making
    external API calls to Supabase. It uses the SUPABASE_JWT_SECRET
    to verify the token signature and expiration.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        Token payload information including:
        - user_id: Supabase user UUID (from 'sub' claim)
        - email: User email
        - role: User role (typically "authenticated")
        - valid: Always True if token is valid
        
    Raises:
        AuthenticationError: If token is missing, invalid, or expired
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")
    
    # Verify token locally using JWT secret (no external API call)
    payload = decode_jwt_token(authorization)
    
    # Extract user information from token payload
    user_id = payload.get("sub") or payload.get("user_id")
    email = payload.get("email")
    role = payload.get("role", "authenticated")
    
    return {
        "user_id": user_id,
        "email": email,
        "role": role,
        "valid": True,
    }


@router.get("/me")
async def get_me(
    user: User = Depends(get_current_user),
):
    """
    Get current authenticated user profile.
    
    Returns:
        User profile data
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "plan": user.plan,
        "credits_remaining": user.credits_remaining,
        "company_name": user.company_name,
        "job_title": user.job_title,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
