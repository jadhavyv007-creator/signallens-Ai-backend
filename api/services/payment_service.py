"""
Decoupled Payment and Subscription Service.
Supports Mock Payment Simulation (UPI/Card) and Razorpay integration.
"""

import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from api.config.env import env
from api.database.repositories import UserRepository, SubscriptionRepository, PaymentRepository
from api.database.models import UserModel, PaymentModel
from api.schemas.common import APIException
from api.schemas.payment import (
    PaymentPlan,
    BillingCycle,
    PaymentCurrency,
    PaymentMethod,
    PaymentGateway,
    PaymentStatus,
    CreateOrderResponse,
    SimulateSuccessResponse,
    OrderDetailsResponse,
    InvoiceBreakdown,
)

# Optional Razorpay import with graceful fallback
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    razorpay = None
    RAZORPAY_AVAILABLE = False


def calculate_pricing(
    plan: str,
    currency: str = "INR",
    billing_cycle: str = "monthly",
) -> Tuple[float, float, float]:
    """
    Deterministic Pricing Matrix:
    - cyber_pro:
      - Monthly: Base ₹2,499 | GST 18% (₹450) | Total ₹2,949
      - Annual: 20% discount on base | 18% GST (Base ₹23,990.4 | GST ₹4,318.27 | Total ₹28,308.67)
    - sovereign:
      - Monthly: Base ₹16,999 | GST 18% (₹3,060) | Total ₹20,059
      - Annual: 20% discount on base | 18% GST (Base ₹163,190.4 | GST ₹29,374.27 | Total ₹192,564.67)
    """
    clean_plan = plan.lower().strip()
    clean_curr = currency.upper().strip()
    clean_cycle = billing_cycle.lower().strip()

    if clean_plan == "cyber_pro":
        if clean_curr == "INR":
            if clean_cycle == "annual":
                base = round(2499.0 * 12 * 0.8, 2)
                tax = round(base * 0.18, 2)
                total = round(base + tax, 2)
            else:
                base = 2499.0
                tax = 450.0  # Matrix 18% GST
                total = 2949.0
        else:
            base = 278.4 if clean_cycle == "annual" else 29.0
            tax = 0.0
            total = base
    elif clean_plan == "sovereign":
        if clean_curr == "INR":
            if clean_cycle == "annual":
                base = round(16999.0 * 12 * 0.8, 2)
                tax = round(base * 0.18, 2)
                total = round(base + tax, 2)
            else:
                base = 16999.0
                tax = 3060.0  # Matrix 18% GST
                total = 20059.0
        else:
            base = 1910.4 if clean_cycle == "annual" else 199.0
            tax = 0.0
            total = base
    else:
        raise APIException(
            status_code=400,
            code="INVALID_PLAN",
            message=f"Unsupported plan '{plan}'. Supported plans: 'cyber_pro' and 'sovereign'.",
        )

    return base, tax, total


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.sub_repo = SubscriptionRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.razorpay_client = None

        if env.is_razorpay_configured and RAZORPAY_AVAILABLE:
            try:
                self.razorpay_client = razorpay.Client(
                    auth=(env.RAZORPAY_KEY_ID, env.RAZORPAY_KEY_SECRET)
                )
            except Exception:
                self.razorpay_client = None

    async def create_order(
        self,
        plan: str,
        currency: str = "INR",
        billing_cycle: str = "monthly",
        payment_method: str = "upi",
        user_id: Optional[str] = None,
    ) -> CreateOrderResponse:
        """
        Creates a payment order in mock simulation mode or Razorpay gateway.
        """
        # 1. Validate User if supplied (gracefully handle Swagger default placeholders like 'string')
        valid_user_id = None
        if user_id:
            candidate = str(user_id).strip()
            if candidate and candidate.lower() not in ("string", "none", "null", ""):
                user = await self.user_repo.get_by_id(candidate)
                if user:
                    valid_user_id = user.id

        # 2. Compute deterministic pricing and GST
        base_amount, tax_amount, total_amount = calculate_pricing(
            plan=plan,
            currency=currency,
            billing_cycle=billing_cycle,
        )

        # 3. Handle Gateway logic (Mock vs Razorpay)
        use_razorpay = (
            not env.ENABLE_MOCK_PAYMENTS 
            and self.razorpay_client is not None
        )

        if use_razorpay:
            try:
                rzp_order = self.razorpay_client.order.create({
                    "amount": int(round(total_amount * 100)),  # in paise
                    "currency": currency.upper(),
                    "receipt": f"rcpt_{uuid.uuid4().hex[:10]}",
                    "notes": {
                        "plan": plan,
                        "billing_cycle": billing_cycle,
                        "user_id": str(valid_user_id) if valid_user_id else "",
                    }
                })
                order_id = rzp_order["id"]
                gateway = "razorpay"
                razorpay_order_id = rzp_order["id"]
                razorpay_key_id = env.RAZORPAY_KEY_ID
                upi_id = None
                mock_simulation_token = None
            except Exception as e:
                raise APIException(
                    status_code=502,
                    code="GATEWAY_ERROR",
                    message=f"Failed to create order with Razorpay: {str(e)}",
                )
        else:
            # Mock mode
            order_id = f"ORD_MOCK_{uuid.uuid4().hex[:12].upper()}"
            gateway = "mock"
            razorpay_order_id = None
            razorpay_key_id = None
            upi_id = "analyst@okhdfcbank"
            mock_simulation_token = f"sim_tok_{uuid.uuid4().hex[:16]}"

        # 4. Insert into payments table as pending
        payment = await self.payment_repo.create_payment(
            order_id=order_id,
            plan=plan.lower().strip(),
            currency=currency.upper().strip(),
            billing_cycle=billing_cycle.lower().strip(),
            base_amount=base_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_method=payment_method.lower().strip(),
            gateway=gateway,
            status="pending",
            user_id=valid_user_id,
            raw_metadata={
                "upi_id": upi_id,
                "mock_simulation_token": mock_simulation_token,
                "razorpay_order_id": razorpay_order_id,
            } if mock_simulation_token or razorpay_order_id else None,
        )

        return CreateOrderResponse(
            order_id=payment.order_id,
            plan=payment.plan,
            currency=payment.currency,
            billing_cycle=payment.billing_cycle,
            base_amount=payment.base_amount,
            tax_amount=payment.tax_amount,
            total_amount=payment.total_amount,
            payment_method=payment.payment_method,
            gateway=payment.gateway,
            status=payment.status,
            upi_id=upi_id,
            mock_simulation_token=mock_simulation_token,
            razorpay_order_id=razorpay_order_id,
            razorpay_key_id=razorpay_key_id,
        )

    async def simulate_success(
        self,
        order_id: str,
        payment_method: Optional[str] = "upi",
    ) -> SimulateSuccessResponse:
        """
        Simulates payment completion for Hackathons / Demos.
        Upgrades the user's tier immediately in local DB if user exists.
        """
        if not order_id:
            raise APIException(
                status_code=400,
                code="INVALID_ORDER_ID",
                message="Order ID must not be empty.",
            )

        clean_order_id = str(order_id).strip()
        payment = await self.payment_repo.get_by_order_id(clean_order_id)
        if not payment:
            raise APIException(
                status_code=404,
                code="ORDER_NOT_FOUND",
                message=f"Order '{clean_order_id}' was not found.",
            )

        # Update order status in DB
        payment = await self.payment_repo.update_status(
            order_id=clean_order_id,
            status="completed",
            payment_method=payment_method or payment.payment_method,
        )

        user_dict = None
        if payment and payment.user_id:
            try:
                user = await self.user_repo.get_by_id(payment.user_id)
                if user:
                    # 1. Upgrade user tier
                    await self.user_repo.update_tier(user.id, payment.plan)

                    # 2. Update subscription record
                    period_days = 365 if payment.billing_cycle == "annual" else 30
                    period_end = datetime.now(timezone.utc) + timedelta(days=period_days)
                    await self.sub_repo.update_subscription(
                        user_id=user.id,
                        tier=payment.plan,
                        billing_cycle=payment.billing_cycle,
                        status="active",
                        period_end=period_end,
                        payment_provider=payment.gateway,
                        provider_sub_id=payment.order_id,
                    )

                    # 3. Log billing event
                    await self.sub_repo.log_billing_event(
                        user_id=user.id,
                        event_type="payment.simulated.success",
                        amount=payment.total_amount,
                        currency=payment.currency,
                        raw_payload={"order_id": payment.order_id, "plan": payment.plan},
                    )

                    user_dict = {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        "role": user.role,
                        "tier": payment.plan,
                    }
            except Exception:
                user_dict = None

        return SimulateSuccessResponse(
            message="Payment simulation successful. Subscription upgraded.",
            order_id=payment.order_id if payment else clean_order_id,
            status="completed",
            plan=payment.plan if payment else "cyber_pro",
            user=user_dict,
        )

    async def get_order_details(self, order_id: str) -> OrderDetailsResponse:
        """
        Fetches payment order details and computes formal invoice breakdown.
        """
        if not order_id:
            raise APIException(
                status_code=400,
                code="INVALID_ORDER_ID",
                message="Order ID must not be empty.",
            )
        clean_order_id = str(order_id).strip()
        payment = await self.payment_repo.get_by_order_id(clean_order_id)
        if not payment:
            raise APIException(
                status_code=404,
                code="ORDER_NOT_FOUND",
                message=f"Payment order '{clean_order_id}' does not exist.",
            )

        plan_display = (
            "Cyber Pro Security Intelligence"
            if payment.plan == "cyber_pro"
            else "Sovereign Defense SIGINT Workbench"
        )

        invoice = InvoiceBreakdown(
            invoice_number=f"INV-{payment.order_id}",
            plan_name=f"{plan_display} ({payment.billing_cycle.capitalize()})",
            base_amount=payment.base_amount,
            tax_rate_percent=18.0 if payment.currency == "INR" else 0.0,
            tax_amount=payment.tax_amount,
            total_amount=payment.total_amount,
            currency=payment.currency,
            status="paid" if payment.status == "completed" else payment.status,
            created_at=payment.created_at,
        )

        return OrderDetailsResponse(
            id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            plan=payment.plan,
            currency=payment.currency,
            billing_cycle=payment.billing_cycle,
            base_amount=payment.base_amount,
            tax_amount=payment.tax_amount,
            total_amount=payment.total_amount,
            payment_method=payment.payment_method,
            gateway=payment.gateway,
            status=payment.status,
            created_at=payment.created_at,
            invoice=invoice,
        )

    async def handle_razorpay_webhook(
        self,
        raw_body: bytes,
        signature: Optional[str],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processes Razorpay server-to-server webhook events (e.g. order.paid, payment.captured).
        """
        if env.is_razorpay_configured and RAZORPAY_AVAILABLE and self.razorpay_client:
            if not signature or not env.RAZORPAY_WEBHOOK_SECRET:
                raise APIException(
                    status_code=400,
                    code="WEBHOOK_SIGNATURE_MISSING",
                    message="Missing Razorpay signature or webhook secret.",
                )
            try:
                self.razorpay_client.utility.verify_webhook_signature(
                    raw_body.decode("utf-8"),
                    signature,
                    env.RAZORPAY_WEBHOOK_SECRET,
                )
            except Exception as e:
                raise APIException(
                    status_code=400,
                    code="INVALID_SIGNATURE",
                    message=f"Razorpay webhook signature verification failed: {str(e)}",
                )

        event = payload.get("event", "order.paid")

        # Extract order ID from webhook payload
        order_id = (
            payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
            or payload.get("payload", {}).get("order", {}).get("entity", {}).get("id")
            or payload.get("order_id")
        )

        if order_id:
            payment = await self.payment_repo.get_by_order_id(order_id)
            if payment:
                await self.payment_repo.update_status(
                    order_id=order_id,
                    status="completed",
                    raw_metadata=payload,
                )
                if payment.user_id:
                    user = await self.user_repo.get_by_id(payment.user_id)
                    if user:
                        await self.user_repo.update_tier(user.id, payment.plan)
                        period_days = 365 if payment.billing_cycle == "annual" else 30
                        await self.sub_repo.update_subscription(
                            user_id=user.id,
                            tier=payment.plan,
                            billing_cycle=payment.billing_cycle,
                            status="active",
                            period_end=datetime.now(timezone.utc) + timedelta(days=period_days),
                            payment_provider=payment.gateway,
                            provider_sub_id=payment.order_id,
                        )

        return {
            "received": True,
            "event": event,
            "order_id": order_id,
        }
