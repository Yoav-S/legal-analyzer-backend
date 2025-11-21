"""
Billing and subscription endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_current_user, get_current_user_id, get_mongodb_db
from app.models.user import User
from app.models.billing import Subscription
from app.services.stripe import StripeService
from app.utils.errors import BillingError, NotFoundError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()
stripe_service = StripeService()


class SubscribeRequest(BaseModel):
    """Request model for subscription."""
    plan: str  # starter, professional, enterprise
    payment_method_id: Optional[str] = None


@router.get("/plans")
async def get_plans():
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price": 29,
                "currency": "USD",
                "interval": "month",
                "document_limit": 20,
                "features": ["Basic analysis", "PDF reports", "Email support"],
            },
            {
                "id": "professional",
                "name": "Professional",
                "price": 79,
                "currency": "USD",
                "interval": "month",
                "document_limit": 100,
                "features": ["Advanced analysis", "Priority processing", "API access", "Email support"],
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 0,  # Custom pricing
                "currency": "USD",
                "interval": "month",
                "document_limit": -1,  # Unlimited
                "features": ["Unlimited documents", "Dedicated support", "Custom integration", "SLA"],
            },
        ]
    }


@router.post("/subscribe")
async def create_subscription(
    request: SubscribeRequest,
    user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """Create or update subscription."""
    # Check if user already has subscription
    existing_sub = await Subscription.get_by_user_id(db, user.user_id)
    
    try:
        if existing_sub and existing_sub.is_active():
            # Update existing subscription
            import stripe
            stripe.Subscription.modify(
                existing_sub.stripe_subscription_id,
                items=[{"id": existing_sub.stripe_subscription_id, "price": stripe_service.PLAN_PRICE_IDS[request.plan]}],
            )
            existing_sub.plan = request.plan
            await existing_sub.save(db)
            return {"message": "Subscription updated", "subscription": existing_sub.model_dump()}
        else:
            # Create new subscription
            if not existing_sub or not existing_sub.stripe_customer_id:
                # Create customer
                customer_id = await stripe_service.create_customer(
                    user.user_id,
                    user.email,
                    user.full_name,
                )
            else:
                customer_id = existing_sub.stripe_customer_id
            
            # Create subscription
            subscription_data = await stripe_service.create_subscription(
                customer_id,
                request.plan,
                request.payment_method_id,
            )
            
            # Save to database
            if existing_sub:
                existing_sub.stripe_subscription_id = subscription_data["subscription_id"]
                existing_sub.plan = request.plan
                existing_sub.status = subscription_data["status"]
                existing_sub.current_period_start = subscription_data["current_period_start"]
                existing_sub.current_period_end = subscription_data["current_period_end"]
                await existing_sub.save(db)
            else:
                subscription = await Subscription.create(
                    db,
                    {
                        "user_id": user.user_id,
                        "stripe_customer_id": customer_id,
                        "stripe_subscription_id": subscription_data["subscription_id"],
                        "plan": request.plan,
                        "status": subscription_data["status"],
                        "current_period_start": subscription_data["current_period_start"],
                        "current_period_end": subscription_data["current_period_end"],
                    },
                )
            
            # Update user plan and credits
            user.plan = request.plan
            monthly_limit = stripe_service.get_plan_limits(request.plan)
            if monthly_limit > 0:
                user.credits_remaining = monthly_limit
            await user.save(db)
            
            return {"message": "Subscription created", "subscription": subscription_data}
            
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise BillingError(f"Failed to create subscription: {str(e)}")


@router.get("/portal")
async def get_customer_portal(
    user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """Get Stripe customer portal URL."""
    subscription = await Subscription.get_by_user_id(db, user.user_id)
    if not subscription or not subscription.stripe_customer_id:
        raise NotFoundError("Subscription", user.user_id)
    
    try:
        portal_url = await stripe_service.get_customer_portal_url(subscription.stripe_customer_id)
        return {"url": portal_url}
    except Exception as e:
        logger.error(f"Error getting portal URL: {e}")
        raise BillingError(f"Failed to get portal URL: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    try:
        event = await stripe_service.handle_webhook(payload, signature)
        
        # Handle different event types
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        # Import here to avoid circular dependency
        from app.queues.tasks import handle_stripe_webhook
        
        # Process webhook asynchronously
        handle_stripe_webhook.delay(event_type, event_data)
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

