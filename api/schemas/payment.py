"""
Payment and Subscription Order Schemas.
Conforms strictly to Pydantic v2 with camelCase and snake_case compatibility.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PaymentPlan(str, Enum):
    CYBER_PRO = "cyber_pro"
    SOVEREIGN = "sovereign"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class PaymentCurrency(str, Enum):
    INR = "INR"
    USD = "USD"


class PaymentMethod(str, Enum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    SIMULATION = "simulation"


class PaymentGateway(str, Enum):
    MOCK = "mock"
    RAZORPAY = "razorpay"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateOrderRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, alias="userId", description="Optional user ID for Swagger testing")
    plan: PaymentPlan = Field(description="Subscription plan: cyber_pro or sovereign")
    currency: PaymentCurrency = Field(default=PaymentCurrency.INR, description="Currency (INR or USD)")
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY, alias="billingCycle", description="Billing frequency (monthly or annual)")
    payment_method: PaymentMethod = Field(default=PaymentMethod.UPI, alias="paymentMethod", description="Selected payment method")

    model_config = ConfigDict(populate_by_name=True)


class CreateOrderResponse(BaseModel):
    order_id: str = Field(alias="orderId", description="Unique order identifier")
    plan: str = Field(description="Plan tier")
    currency: str = Field(description="Currency code")
    billing_cycle: str = Field(alias="billingCycle")
    base_amount: float = Field(alias="baseAmount")
    tax_amount: float = Field(alias="taxAmount")
    total_amount: float = Field(alias="totalAmount")
    payment_method: str = Field(alias="paymentMethod")
    gateway: str
    status: str
    upi_id: Optional[str] = Field(default=None, alias="upiId", description="Dummy or configured UPI ID for mock orders")
    mock_simulation_token: Optional[str] = Field(default=None, alias="mockSimulationToken")
    razorpay_order_id: Optional[str] = Field(default=None, alias="razorpayOrderId")
    razorpay_key_id: Optional[str] = Field(default=None, alias="razorpayKeyId")

    model_config = ConfigDict(populate_by_name=True)


class SimulateSuccessRequest(BaseModel):
    order_id: str = Field(alias="orderId", description="Order ID to simulate payment success for")
    payment_method: Optional[PaymentMethod] = Field(default=PaymentMethod.UPI, alias="paymentMethod")

    model_config = ConfigDict(populate_by_name=True)


class SimulateSuccessResponse(BaseModel):
    message: str = "Payment simulation successful. Subscription upgraded."
    order_id: str = Field(alias="orderId")
    status: str = "completed"
    plan: str
    user: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class InvoiceBreakdown(BaseModel):
    invoice_number: str = Field(alias="invoiceNumber")
    plan_name: str = Field(alias="planName")
    base_amount: float = Field(alias="baseAmount")
    tax_rate_percent: float = Field(default=18.0, alias="taxRatePercent")
    tax_amount: float = Field(alias="taxAmount")
    total_amount: float = Field(alias="totalAmount")
    currency: str
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class OrderDetailsResponse(BaseModel):
    id: str
    order_id: str = Field(alias="orderId")
    user_id: Optional[str] = Field(default=None, alias="userId")
    plan: str
    currency: str
    billing_cycle: str = Field(alias="billingCycle")
    base_amount: float = Field(alias="baseAmount")
    tax_amount: float = Field(alias="taxAmount")
    total_amount: float = Field(alias="totalAmount")
    payment_method: str = Field(alias="paymentMethod")
    gateway: str
    status: str
    created_at: datetime = Field(alias="createdAt")
    invoice: Optional[InvoiceBreakdown] = None

    model_config = ConfigDict(populate_by_name=True)
