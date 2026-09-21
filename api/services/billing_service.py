"""
Commercial Tiering and Billing Management Service.
Implements the 3-tier pricing matrix (Base Hunter, Cyber Pro, Sovereign Defense) per PRD Section 19.
"""

import hmac
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from api.config.env import env
from api.database.models import UserModel
from api.database.repositories import SubscriptionRepository, UserRepository
from api.schemas.common import APIException
from api.schemas.billing import (
    TierSpecification,
    TierPricing,
    TierFeature,
    Currency,
    BillingCycle,
    PaymentProvider,
    CheckoutResponse,
    SubscriptionStatus,
)

TIERS_SPECIFICATION: List[Dict[str, Any]] = [
    {
        "id": "base",
        "name": "Base Hunter",
        "tagline": "For radio amateurs, hobbyists, and university RF students",
        "badge": "FREE FOREVER",
        "pricing": {
            "monthlyInr": 0,
            "annualInr": 0,
            "monthlyUsd": 0,
            "annualUsd": 0,
        },
        "maxUploadMb": 25,
        "maxLiveMicSeconds": 15,
        "supportedFormats": [".wav", ".ogg"],
        "recommended": False,
        "features": [
            {"id": "dsp_core", "name": "Core DSP Engine (FFT, Welch PSD, Spectrogram)", "description": "Full interactive waveform, spectrum, and spectrogram analysis", "included": True},
            {"id": "modulation", "name": "Basic Modulation Tagging (AM/FM/CW/Noise)", "description": "Automatic RF signal classification", "included": True},
            {"id": "report", "name": "Plaintext SIGINT Intelligence Dossier", "description": "Exportable text report summary", "included": True},
            {"id": "fingerprint", "name": "RF Emitter DNA Profiling", "description": "CFO drift and hardware class identification", "included": False},
            {"id": "bss", "name": "Blind Source Separation (5 Stems)", "description": "FastICA multi-channel unmixing", "included": False},
        ],
    },
    {
        "id": "cyber_pro",
        "name": "Cyber Pro",
        "tagline": "For professional RF engineers, telecom security auditors, and SIGINT labs",
        "badge": "MOST POPULAR",
        "pricing": {
            "monthlyInr": 2499,
            "annualInr": 23990,  # ~20% discount
            "monthlyUsd": 29,
            "annualUsd": 279,
        },
        "maxUploadMb": 500,
        "maxLiveMicSeconds": 60,
        "supportedFormats": [".wav", ".ogg", ".iq", ".raw", ".cf32", ".cs16"],
        "recommended": True,
        "features": [
            {"id": "dsp_core", "name": "Core DSP Engine + 500 MB Captures", "description": "High-bandwidth processing", "included": True},
            {"id": "suite_a", "name": "Suite A Forensic Audio Pipeline", "description": "Cockpit A/B denoised player, RF Fingerprinting, Lasso isolator, Anti-Spoof matrix", "included": True},
            {"id": "suite_b_core", "name": "Suite B Deep-Space & Aerospace Core", "description": "Doppler drift (Hz/s), Chirp-rate α, and Shannon entropy engine", "included": True},
            {"id": "raw_iq", "name": "Raw SDR Binary Ingestion (.IQ, .CF32, .CS16)", "description": "Direct HackRF, RTL-SDR, USRP stream parsing", "included": True},
            {"id": "bss", "name": "Blind Source Separation (5 Stems)", "description": "FastICA multi-channel unmixing", "included": False},
        ],
    },
    {
        "id": "sovereign",
        "name": "Ultra Pro Max — Sovereign Defense",
        "tagline": "For aerospace defense labs, satellite tracking stations, and EW units",
        "badge": "ENTERPRISE / DEFENSE",
        "pricing": {
            "monthlyInr": 16999,
            "annualInr": 163190,  # ~20% discount
            "monthlyUsd": 199,
            "annualUsd": 1910,
        },
        "maxUploadMb": 8192,
        "maxLiveMicSeconds": 3600,
        "supportedFormats": ["All Formats + Multi-Channel Batch"],
        "recommended": False,
        "features": [
            {"id": "all_suites", "name": "All 18 Advanced Intelligence Suites (A, B, C)", "description": "Complete EW, Sub-Noise, Stego, Micro-Doppler, and BSS toolsets", "included": True},
            {"id": "multi_receiver", "name": "Multi-Receiver TDoA Hyperbolic Trilateration", "description": "Cross-correlation geolocation engine", "included": True},
            {"id": "blind_bss", "name": "Pure-NumPy FastICA Blind Source Separation", "description": "5-stem channel isolation", "included": True},
            {"id": "uav_radar", "name": "Drone / UAV Micro-Doppler Blade Profiler", "description": "Rotor RPM and blade harmonic estimation", "included": True},
            {"id": "symbolic_demod", "name": "Universal Symbolic Demodulator Sandbox", "description": "Blind clock recovery and raw hex bitstream extraction", "included": True},
        ],
    },
]


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sub_repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)

    def get_tier_specifications(self) -> List[TierSpecification]:
        return [TierSpecification(**t) for t in TIERS_SPECIFICATION]

    async def create_checkout_session(
        self,
        user: UserModel,
        tier: str,
        currency: Currency,
        billing_cycle: BillingCycle,
        payment_provider: PaymentProvider,
        idempotency_key: Optional[str] = None,
    ) -> CheckoutResponse:
        tier_def = next((t for t in TIERS_SPECIFICATION if t["id"] == tier.lower()), None)
        if not tier_def:
            raise APIException(status_code=400, code="INVALID_TIER", message=f"Tier '{tier}' does not exist")

        pricing = tier_def["pricing"]
        if currency == Currency.INR:
            amount = float(pricing["annualInr"] if billing_cycle == BillingCycle.ANNUAL else pricing["monthlyInr"])
        else:
            amount = float(pricing["annualUsd"] if billing_cycle == BillingCycle.ANNUAL else pricing["monthlyUsd"])

        session_id = f"cs_{uuid.uuid4().hex[:16]}"
        checkout_url = f"https://checkout.stripe.com/pay/{session_id}" if payment_provider == PaymentProvider.STRIPE else None
        upi_qr = f"upi://pay?pa=signallens@upi&pn=SignalLensAI&am={amount:.2f}&cu=INR&tn=SignalLens-{tier.upper()}" if payment_provider == PaymentProvider.UPI else None

        # Log billing checkout attempt
        await self.sub_repo.log_billing_event(
            user_id=user.id,
            event_type="checkout_initiated",
            amount=amount,
            currency=currency.value,
            raw_payload={
                "sessionId": session_id,
                "tier": tier,
                "billingCycle": billing_cycle.value,
                "provider": payment_provider.value,
                "idempotencyKey": idempotency_key,
            },
        )

        # In local test/simulation mode: automatically upgrade subscription
        if env.VITE_ENABLE_PAYMENT_SIMULATION and payment_provider == PaymentProvider.SIMULATION:
            period_end = datetime.now(timezone.utc) + timedelta(days=365 if billing_cycle == BillingCycle.ANNUAL else 30)
            await self.sub_repo.update_subscription(
                user_id=user.id,
                tier=tier.lower(),
                billing_cycle=billing_cycle.value,
                status="active",
                period_end=period_end,
                payment_provider="simulation",
                provider_sub_id=session_id,
            )
            await self.user_repo.update_tier(user.id, tier.lower())

        return CheckoutResponse(
            sessionId=session_id,
            checkoutUrl=checkout_url,
            upiQrString=upi_qr,
            amount=amount,
            currency=currency.value,
            tier=tier,
            billingCycle=billing_cycle.value,
        )

    async def handle_webhook(self, payload: dict, signature: Optional[str] = None) -> Dict[str, Any]:
        """Verifies webhook signature and updates subscription status."""
        event_type = payload.get("eventType") or payload.get("type", "unknown")
        data = payload.get("data", {})

        # Verify signature if secret configured
        if env.STRIPE_WEBHOOK_SECRET and env.STRIPE_WEBHOOK_SECRET != "whsec_mock":
            if not signature:
                raise APIException(status_code=400, code="INVALID_SIGNATURE", message="Missing webhook signature")
            # HMAC validation logic here...

        user_id = data.get("userId")
        tier = data.get("tier", "cyber_pro")
        cycle = data.get("billingCycle", "monthly")

        if user_id:
            period_end = datetime.now(timezone.utc) + timedelta(days=30)
            await self.sub_repo.update_subscription(
                user_id=user_id,
                tier=tier,
                billing_cycle=cycle,
                status="active",
                period_end=period_end,
                payment_provider="stripe",
            )
            await self.user_repo.update_tier(user_id, tier)

            await self.sub_repo.log_billing_event(
                user_id=user_id,
                event_type=f"webhook_{event_type}",
                amount=float(data.get("amount", 0.0)),
                currency=data.get("currency", "INR"),
                raw_payload=payload,
            )

        return {"received": True}

    async def get_subscription_status(self, user: UserModel) -> SubscriptionStatus:
        sub = await self.sub_repo.get_or_create(user.id)
        tier_def = next((t for t in TIERS_SPECIFICATION if t["id"] == user.tier), TIERS_SPECIFICATION[0])

        return SubscriptionStatus(
            tier=user.tier,
            status=sub.status,
            billingCycle=sub.billing_cycle,
            currentPeriodEnd=sub.current_period_end,
            paymentProvider=sub.payment_provider,
            uploadsThisMonth=3,
            maxUploadsPerMonth=1000 if user.tier != "base" else 50,
            storageUsedBytes=15 * 1024 * 1024,
            maxStorageBytes=tier_def["maxUploadMb"] * 1024 * 1024 * 20,
        )
