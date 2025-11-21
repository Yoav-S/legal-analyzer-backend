"""
User MongoDB model.
"""
from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from app.utils.errors import NotFoundError


class User(BaseModel):
    """User model for MongoDB."""
    
    user_id: str = Field(..., description="Supabase user ID (UUID)")
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    plan: str = Field(default="starter", description="Subscription plan: starter, professional, enterprise")
    credits_remaining: int = Field(default=0, description="Document analysis credits remaining")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "lawyer@example.com",
                "full_name": "John Doe",
                "plan": "professional",
                "credits_remaining": 75,
                "created_at": "2025-01-15T12:00:00Z",
            }
        }
    
    @classmethod
    async def get_by_id(cls, db: AsyncIOMotorDatabase, user_id: str) -> Optional["User"]:
        """Get user by ID."""
        collection = db.users
        doc = await collection.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return cls(**doc)
        return None
    
    @classmethod
    async def create(cls, db: AsyncIOMotorDatabase, user_data: dict) -> "User":
        """Create new user."""
        collection = db.users
        user = cls(**user_data)
        await collection.insert_one(user.model_dump())
        return user
    
    async def save(self, db: AsyncIOMotorDatabase) -> "User":
        """Save user to database."""
        collection = db.users
        await collection.update_one(
            {"user_id": self.user_id},
            {"$set": self.model_dump()},
            upsert=True,
        )
        return self
    
    async def update_credits(self, db: AsyncIOMotorDatabase, credits: int) -> "User":
        """Update user credits."""
        self.credits_remaining = max(0, self.credits_remaining + credits)
        await self.save(db)
        return self
    
    async def consume_credit(self, db: AsyncIOMotorDatabase) -> bool:
        """
        Consume one credit if available.
        
        Returns:
            True if credit consumed, False if insufficient credits
        """
        if self.credits_remaining <= 0:
            return False
        
        self.credits_remaining -= 1
        await self.save(db)
        return True
    
    def get_plan_limits(self) -> dict:
        """Get document limits for current plan."""
        limits = {
            "starter": 20,
            "professional": 100,
            "enterprise": -1,  # Unlimited
        }
        return {
            "monthly_limit": limits.get(self.plan, 20),
            "credits_remaining": self.credits_remaining,
        }

