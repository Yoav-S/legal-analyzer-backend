"""
Stripe payment and subscription service.
"""
import stripe
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for Stripe payment processing."""
    
    # Plan price IDs (configure in Stripe dashboard)
    PLAN_PRICE_IDS = {
        "starter": settings.STRIPE_PRICE_ID_STARTER,
        "professional": settings.STRIPE_PRICE_ID_PROFESSIONAL,
        "enterprise": settings.STRIPE_PRICE_ID_ENTERPRISE,
    }
    
    # Plan limits
    PLAN_LIMITS = {
        "starter": 20,
        "professional": 100,
        "enterprise": -1,  # Unlimited
    }
    
    async def create_customer(self, user_id: str, email: str, name: Optional[str] = None) -> str:
        """
        Create Stripe customer.
        
        Args:
            user_id: User ID
            email: User email
            name: User name (optional)
            
        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id},
            )
            return customer.id
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {e}")
            raise
    
    async def create_subscription(
        self,
        customer_id: str,
        plan: str,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create subscription for customer.
        
        Args:
            customer_id: Stripe customer ID
            plan: Plan name (starter, professional, enterprise)
            payment_method_id: Payment method ID (optional)
            
        Returns:
            Subscription data
        """
        price_id = self.PLAN_PRICE_IDS.get(plan)
        if not price_id:
            raise ValueError(f"Invalid plan: {plan}")
        
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
            }
            
            if payment_method_id:
                subscription_data["default_payment_method"] = payment_method_id
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            return {
                "subscription_id": subscription.id,
                "customer_id": subscription.customer,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "plan": plan,
            }
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise
    
    async def get_customer_portal_url(self, customer_id: str) -> str:
        """
        Get Stripe customer portal URL.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Portal URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{settings.API_BASE_URL}/billing",
            )
            return session.url
        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            raise
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            
        Returns:
            Event data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            
            return {
                "type": event["type"],
                "data": event["data"],
            }
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
    
    def get_plan_limits(self, plan: str) -> int:
        """Get monthly document limit for plan."""
        return self.PLAN_LIMITS.get(plan, 20)

