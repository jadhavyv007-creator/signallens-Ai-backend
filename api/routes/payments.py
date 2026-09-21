"""
Payment and Subscription Router.
Provides modular endpoints for Mock Payment Simulation and Razorpay order management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.database.db import get_db
from api.schemas.common import APIResponse, APIException
from api.schemas.payment import (
    CreateOrderRequest,
    CreateOrderResponse,
    SimulateSuccessRequest,
    SimulateSuccessResponse,
    OrderDetailsResponse,
)
from api.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments & Subscriptions"])


@router.post("/create-order", response_model=APIResponse[CreateOrderResponse], status_code=status.HTTP_200_OK)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a payment order for Cyber Pro or Sovereign plans.
    In Mock Mode (default): generates deterministic pricing, 18% GST, dummy UPI details, and simulation token.
    In Razorpay Mode: initiates an official Razorpay order when credentials are provided.
    """
    service = PaymentService(db)
    order = await service.create_order(
        plan=body.plan.value if hasattr(body.plan, "value") else str(body.plan),
        currency=body.currency.value if hasattr(body.currency, "value") else str(body.currency),
        billing_cycle=body.billing_cycle.value if hasattr(body.billing_cycle, "value") else str(body.billing_cycle),
        payment_method=body.payment_method.value if hasattr(body.payment_method, "value") else str(body.payment_method),
        user_id=body.user_id,
    )
    return APIResponse(data=order)


@router.post("/simulate-success", response_model=APIResponse[SimulateSuccessResponse], status_code=status.HTTP_200_OK)
async def simulate_success(
    request: Request,
    body: Optional[SimulateSuccessRequest] = None,
    order_id: Optional[str] = Query(None, alias="orderId", description="Optional Order ID in query params"),
    payment_method: Optional[str] = Query(None, alias="paymentMethod", description="Optional Payment Method in query params"),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulates payment completion for Demo/Hackathon testing.
    Instantly marks order as completed and upgrades the user's tier in the database.
    Supports JSON request body, query parameter (?orderId=...), or raw JSON fallback.
    """
    target_order_id = None
    target_method = "upi"

    # 1. Try from parsed body
    if body and body.order_id:
        target_order_id = body.order_id
        if body.payment_method:
            target_method = body.payment_method.value if hasattr(body.payment_method, "value") else str(body.payment_method)

    # 2. Try from query parameters
    if not target_order_id and order_id:
        target_order_id = order_id
    if payment_method:
        target_method = payment_method

    # 3. Fallback to direct JSON parsing if body was omitted or parsed raw
    if not target_order_id:
        try:
            raw = await request.json()
            if isinstance(raw, dict):
                target_order_id = raw.get("orderId") or raw.get("order_id")
                target_method = raw.get("paymentMethod") or raw.get("payment_method") or target_method
        except Exception:
            pass

    if not target_order_id:
        raise APIException(
            status_code=400,
            code="INVALID_ORDER_ID",
            message="Order ID must be provided in request body or as a query parameter (orderId).",
        )

    service = PaymentService(db)
    result = await service.simulate_success(
        order_id=str(target_order_id).strip(),
        payment_method=target_method,
    )
    return APIResponse(data=result)


@router.get("/orders/{order_id}", response_model=APIResponse[OrderDetailsResponse], status_code=status.HTTP_200_OK)
async def get_order_details(
    order_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves payment order status, transaction metadata, and structured invoice breakdown.
    """
    service = PaymentService(db)
    order_details = await service.get_order_details(order_id)
    return APIResponse(data=order_details)


@router.post("/webhook", response_model=APIResponse[dict], status_code=status.HTTP_200_OK)
async def handle_payment_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receives and processes official Razorpay server-to-server webhook events (order.paid).
    """
    service = PaymentService(db)
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    res = await service.handle_razorpay_webhook(
        raw_body=raw_body,
        signature=x_razorpay_signature,
        payload=payload,
    )
    return APIResponse(data=res)
