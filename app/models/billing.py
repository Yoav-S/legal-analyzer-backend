"""
Billing and subscription MongoDB model.
"""
from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field


class Subscription(BaseModel):
    """Subscription model for MongoDB."""
    
    user_id: str = Field(..., description="User ID")
    stripe_customer_id: str = Field(..., description="Stripe customer ID")
    stripe_subscription_id: str = Field(..., description="Stripe subscription ID")
    plan: str = Field(..., description="Plan: starter, professional, enterprise")
    status: str = Field(..., description="Status: active, canceled, past_due, etc.")
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "stripe_customer_id": "cus_...",
                "stripe_subscription_id": "sub_...",
                "plan": "professional",
                "status": "active",
                "current_period_start": "2025-01-01T00:00:00Z",
                "current_period_end": "2025-02-01T00:00:00Z",
            }
        }
    
    @classmethod
    async def get_by_user_id(cls, db: AsyncIOMotorDatabase, user_id: str) -> Optional["Subscription"]:
        """Get subscription by user ID."""
        collection = db.subscriptions
        doc = await collection.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return cls(**doc)
        return None
    
    @classmethod
    async def get_by_stripe_subscription_id(cls, db: AsyncIOMotorDatabase, stripe_subscription_id: str) -> Optional["Subscription"]:
        """Get subscription by Stripe subscription ID."""
        collection = db.subscriptions
        doc = await collection.find_one({"stripe_subscription_id": stripe_subscription_id})
        if doc:
            doc.pop("_id", None)
            return cls(**doc)
        return None
    
    @classmethod
    async def create(cls, db: AsyncIOMotorDatabase, subscription_data: dict) -> "Subscription":
        """Create new subscription."""
        collection = db.subscriptions
        subscription = cls(**subscription_data)
        await collection.insert_one(subscription.model_dump())
        return subscription
    
    async def save(self, db: AsyncIOMotorDatabase) -> "Subscription":
        """Save subscription to database."""
        collection = db.subscriptions
        self.updated_at = datetime.utcnow()
        await collection.update_one(
            {"user_id": self.user_id},
            {"$set": self.model_dump()},
            upsert=True,
        )
        return self
    
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == "active" and datetime.utcnow() < self.current_period_end

