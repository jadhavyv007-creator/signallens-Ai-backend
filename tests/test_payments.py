"""
Unit and Integration Tests for Payments & Subscription Module.
Tests Mock Simulation, Pricing Rule Matrix, Swagger-compatible order creation, and Webhooks.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.database.db import init_db
from api.services.payment_service import calculate_pricing


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_pricing_rule_matrix():
    # 1. Cyber Pro Monthly (INR)
    base, tax, total = calculate_pricing("cyber_pro", currency="INR", billing_cycle="monthly")
    assert base == 2499.0
    assert tax == 450.0
    assert total == 2949.0

    # 2. Cyber Pro Annual (INR) - 20% discount
    base_ann, tax_ann, total_ann = calculate_pricing("cyber_pro", currency="INR", billing_cycle="annual")
    assert base_ann == 23990.4
    assert tax_ann == 4318.27
    assert total_ann == 28308.67

    # 3. Sovereign Monthly (INR)
    base_sov, tax_sov, total_sov = calculate_pricing("sovereign", currency="INR", billing_cycle="monthly")
    assert base_sov == 16999.0
    assert tax_sov == 3060.0
    assert total_sov == 20059.0

    # 4. Sovereign Annual (INR) - 20% discount
    base_sov_ann, tax_sov_ann, total_sov_ann = calculate_pricing("sovereign", currency="INR", billing_cycle="annual")
    assert base_sov_ann == 163190.4
    assert tax_sov_ann == 29374.27
    assert total_sov_ann == 192564.67


@pytest.mark.asyncio
async def test_create_order_mock_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create order without user_id (Swagger UI decoupled test)
        res = await client.post(
            "/api/v1/payments/create-order",
            json={
                "plan": "cyber_pro",
                "currency": "INR",
                "billingCycle": "monthly",
                "paymentMethod": "upi",
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        order = data["data"]
        assert order["orderId"].startswith("ORD_MOCK_")
        assert order["plan"] == "cyber_pro"
        assert order["currency"] == "INR"
        assert order["baseAmount"] == 2499.0
        assert order["taxAmount"] == 450.0
        assert order["totalAmount"] == 2949.0
        assert order["status"] == "pending"
        assert order["upiId"] == "analyst@okhdfcbank"
        assert order["mockSimulationToken"] is not None


@pytest.mark.asyncio
async def test_simulate_success_flow():
    import uuid
    unique_email = f"sim_buyer_{uuid.uuid4().hex[:6]}@defense.gov"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a test user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "Password123!", "name": "Sim Buyer"}
        )
        assert reg_res.status_code == 200

        # Verify OTP to get user record
        otp_res = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": unique_email, "otp": "123456", "name": "Sim Buyer"}
        )
        assert otp_res.status_code == 200
        user_info = otp_res.json()["data"]["user"]
        user_id = user_info["id"]
        assert user_info["tier"] == "base"

        # 2. Create order for Sovereign tier with user_id
        order_res = await client.post(
            "/api/v1/payments/create-order",
            json={
                "userId": user_id,
                "plan": "sovereign",
                "currency": "INR",
                "billingCycle": "monthly",
                "paymentMethod": "upi",
            }
        )
        assert order_res.status_code == 200
        order_id = order_res.json()["data"]["orderId"]

        # 3. Simulate payment success
        sim_res = await client.post(
            "/api/v1/payments/simulate-success",
            json={"orderId": order_id, "paymentMethod": "upi"}
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()["data"]
        assert sim_data["status"] == "completed"
        assert sim_data["plan"] == "sovereign"
        assert sim_data["user"]["tier"] == "sovereign"

        # 4. Fetch invoice / order breakdown
        inv_res = await client.get(f"/api/v1/payments/orders/{order_id}")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()["data"]
        assert inv_data["orderId"] == order_id
        assert inv_data["status"] == "completed"
        assert inv_data["invoice"]["status"] == "paid"
        assert inv_data["invoice"]["invoiceNumber"] == f"INV-{order_id}"
        assert inv_data["invoice"]["totalAmount"] == 20059.0


@pytest.mark.asyncio
async def test_order_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/payments/orders/ORD_MOCK_DOESNOTEXIST")
        assert res.status_code == 404
        assert res.json()["success"] is False
        assert res.json()["error"]["code"] == "ORDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_swagger_decoupled_simulation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create order with Swagger default string placeholder
        res = await client.post(
            "/api/v1/payments/create-order",
            json={
                "userId": "string",
                "plan": "cyber_pro",
                "currency": "INR",
                "billingCycle": "monthly",
                "paymentMethod": "upi",
            }
        )
        assert res.status_code == 200
        order_id = res.json()["data"]["orderId"]

        # 2. Simulate success immediately with lowercase and whitespace
        sim_res = await client.post(
            "/api/v1/payments/simulate-success",
            json={
                "orderId": f"  {order_id.lower()}  ",
                "paymentMethod": "upi"
            }
        )
        assert sim_res.status_code == 200
        assert sim_res.json()["success"] is True
        assert sim_res.json()["data"]["status"] == "completed"
        assert sim_res.json()["data"]["plan"] == "cyber_pro"

        # 3. Order lookup with original ID
        lookup_res = await client.get(f"/api/v1/payments/orders/{order_id}")
        assert lookup_res.status_code == 200
        assert lookup_res.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_payment_webhook():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/payments/webhook",
            json={
                "event": "order.paid",
                "order_id": "ORD_MOCK_TEST_WEBHOOK",
                "payload": {}
            }
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["data"]["received"] is True
