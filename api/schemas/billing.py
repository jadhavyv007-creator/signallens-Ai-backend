"""
Billing and commercial subscription schemas (Pydantic v2 with camelCase aliases).
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Currency(str, Enum):
    INR = "INR"
    USD = "USD"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    UPI = "upi"
    SIMULATION = "simulation"


class TierPricing(BaseModel):
    monthly_inr: int = Field(alias="monthlyInr")
    annual_inr: int = Field(alias="annualInr")
    monthly_usd: int = Field(alias="monthlyUsd")
    annual_usd: int = Field(alias="annualUsd")

    model_config = ConfigDict(populate_by_name=True)


class TierFeature(BaseModel):
    id: str
    name: str
    description: str
    included: bool

    model_config = ConfigDict(populate_by_name=True)


class TierSpecification(BaseModel):
    id: str
    name: str
    tagline: str
    badge: Optional[str] = None
    pricing: TierPricing
    max_upload_mb: int = Field(alias="maxUploadMb")
    max_live_mic_seconds: int = Field(alias="maxLiveMicSeconds")
    supported_formats: List[str] = Field(alias="supportedFormats")
    features: List[TierFeature]
    recommended: bool = False

    model_config = ConfigDict(populate_by_name=True)


class CheckoutRequest(BaseModel):
    tier: str
    currency: Currency = Currency.INR
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY, alias="billingCycle")
    payment_provider: PaymentProvider = Field(default=PaymentProvider.STRIPE, alias="paymentProvider")
    idempotency_key: Optional[str] = Field(default=None, alias="idempotencyKey")

    model_config = ConfigDict(populate_by_name=True)


class CheckoutResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    checkout_url: Optional[str] = Field(default=None, alias="checkoutUrl")
    upi_qr_string: Optional[str] = Field(default=None, alias="upiQrString")
    amount: float
    currency: str
    tier: str
    billing_cycle: str = Field(alias="billingCycle")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionStatus(BaseModel):
    tier: str
    status: str
    billing_cycle: str = Field(alias="billingCycle")
    current_period_end: datetime = Field(alias="currentPeriodEnd")
    payment_provider: str = Field(alias="paymentProvider")
    uploads_this_month: int = Field(alias="uploadsThisMonth")
    max_uploads_per_month: int = Field(alias="maxUploadsPerMonth")
    storage_used_bytes: int = Field(alias="storageUsedBytes")
    max_storage_bytes: int = Field(alias="maxStorageBytes")

    model_config = ConfigDict(populate_by_name=True)


class WebhookPayload(BaseModel):
    event_type: str = Field(alias="eventType")
    event_id: str = Field(alias="eventId")
    data: Dict[str, Any]
    signature: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
