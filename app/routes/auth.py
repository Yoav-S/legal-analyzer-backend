"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, Header
from typing import Optional

from app.dependencies import get_current_user, get_current_user_id, get_supabase_service
from app.models.user import User
from app.utils.errors import AuthenticationError

router = APIRouter()


@router.post("/verify-token")
async def verify_token(
    authorization: Optional[str] = Header(None),
    supabase: Depends = Depends(get_supabase_service),
):
    """
    Verify Supabase JWT token.
    
    Returns:
        User information if token is valid
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")
    
    # Remove 'Bearer ' prefix
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    # Verify with Supabase
    user_data = await supabase.verify_token(token)
    if not user_data:
        raise AuthenticationError("Invalid token")
    
    return {
        "user_id": user_data.get("id"),
        "email": user_data.get("email"),
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

