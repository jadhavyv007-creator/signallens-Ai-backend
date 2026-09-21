"""
Commercial Billing, Pricing Matrix & Subscription Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.database.db import get_db
from api.database.models import UserModel
from api.middleware.auth_guard import get_current_user
from api.services.billing_service import BillingService
from api.schemas.common import APIResponse
from api.schemas.billing import (
    TierSpecification,
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionStatus,
    WebhookPayload,
)

router = APIRouter(prefix="/api/v1/billing", tags=["Billing & Subscriptions"])


@router.get("/tiers", response_model=APIResponse[List[TierSpecification]])
async def get_pricing_tiers(
    db: AsyncSession = Depends(get_db),
):
    """Returns the commercial tier specification and pricing matrix (source of truth for frontend)."""
    service = BillingService(db)
    tiers = service.get_tier_specifications()
    return APIResponse(data=tiers)


@router.post("/checkout", response_model=APIResponse[CheckoutResponse])
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a Stripe or UPI checkout session."""
    service = BillingService(db)
    checkout = await service.create_checkout_session(
        user=current_user,
        tier=body.tier,
        currency=body.currency,
        billing_cycle=body.billing_cycle,
        payment_provider=body.payment_provider,
        idempotency_key=body.idempotency_key,
    )
    return APIResponse(data=checkout)


@router.post("/webhook", response_model=APIResponse[dict])
async def handle_payment_webhook(
    request: Request,
    body: WebhookPayload,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Receives server-to-server signed payment webhooks from Stripe/UPI gateways."""
    service = BillingService(db)
    raw_dict = body.model_dump(by_alias=True)
    res = await service.handle_webhook(payload=raw_dict, signature=stripe_signature)
    return APIResponse(data=res)


@router.get("/me", response_model=APIResponse[SubscriptionStatus])
async def get_current_subscription(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns current user tier, usage meters, and billing renewal dates."""
    service = BillingService(db)
    sub_status = await service.get_subscription_status(current_user)
    return APIResponse(data=sub_status)
