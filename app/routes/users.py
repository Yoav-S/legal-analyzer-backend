"""
User management endpoints.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.dependencies import get_current_user, get_mongodb_db
from app.models.user import User
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


class UpdateUserRequest(BaseModel):
    """Request model for updating user profile."""
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None


@router.get("/profile")
async def get_profile(
    user: User = Depends(get_current_user),
):
    """Get user profile."""
    return user.model_dump()


@router.patch("/profile")
async def update_profile(
    request: UpdateUserRequest,
    user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """Update user profile."""
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.company_name is not None:
        user.company_name = request.company_name
    if request.job_title is not None:
        user.job_title = request.job_title
    
    await user.save(db)
    return user.model_dump()

