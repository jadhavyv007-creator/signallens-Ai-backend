"""
Integration tests for Authentication, Token Rotation, Lockout, and Commercial Billing.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow():
    transport = ASGITransport(app=app)
    unique_email = f"operator_{uuid.uuid4().hex[:8]}@defense.gov"
    password = "StrongPassword123!"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register (Sends 6-digit OTP)
        reg_payload = {"email": unique_email, "password": password, "name": "Chief Signal Officer"}
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 200
        assert "message" in res.json()["data"]

        # 2. Verify OTP
        otp_res = await client.post("/api/v1/auth/verify-otp", json={"email": unique_email, "otp": "123456", "name": "Chief Signal Officer"})
        assert otp_res.status_code == 200
        data = otp_res.json()["data"]
        assert "accessToken" in data
        assert data["user"]["email"] == unique_email.lower()

        # Check refresh cookie was set
        assert "refreshToken" in otp_res.cookies
        refresh_cookie = otp_res.cookies.get("refreshToken")
        access_token = data["accessToken"]

        # 3. Access /users/me
        me_res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me_res.status_code == 200
        assert me_res.json()["data"]["email"] == unique_email.lower()

        # 4. Refresh token rotation
        ref_res = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"refreshToken={refresh_cookie}"})
        assert ref_res.status_code == 200
        new_access_token = ref_res.json()["data"]["accessToken"]
        assert new_access_token is not None
        assert "refreshToken" in ref_res.cookies
        new_refresh_cookie = ref_res.cookies.get("refreshToken")

        # 5. Old refresh token should be rejected (breach detection / rotation)
        async with AsyncClient(transport=transport, base_url="http://test") as client2:
            old_ref_res = await client2.post("/api/v1/auth/refresh", headers={"Cookie": f"refreshToken={refresh_cookie}"})
            assert old_ref_res.status_code == 401
            assert old_ref_res.json()["error"]["code"] in ("REFRESH_TOKEN_REUSED", "REFRESH_TOKEN_INVALID")


@pytest.mark.asyncio
async def test_billing_tiers_and_simulated_checkout():
    transport = ASGITransport(app=app)
    unique_email = f"pro_{uuid.uuid4().hex[:8]}@telecom.net"
    password = "ProPassword123!"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Public tiers
        tiers_res = await client.get("/api/v1/billing/tiers")
        assert tiers_res.status_code == 200
        tiers = tiers_res.json()["data"]
        assert len(tiers) == 3
        assert tiers[0]["id"] == "base"
        assert tiers[1]["id"] == "cyber_pro"
        assert tiers[2]["id"] == "sovereign"

        # 2. Register user + Verify OTP
        await client.post("/api/v1/auth/register", json={"email": unique_email, "password": password})
        verify_res = await client.post("/api/v1/auth/verify-otp", json={"email": unique_email, "otp": "123456"})
        token = verify_res.json()["data"]["accessToken"]

        # 3. Upgrade to Sovereign Defense via simulated checkout
        checkout_payload = {
            "tier": "sovereign",
            "currency": "INR",
            "billingCycle": "annual",
            "paymentProvider": "simulation",
        }
        co_res = await client.post(
            "/api/v1/billing/checkout",
            json=checkout_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert co_res.status_code == 200
        assert co_res.json()["data"]["tier"] == "sovereign"

        # 4. Refresh /users/me - tier should now be sovereign
        me_res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.json()["data"]["tier"] == "sovereign"

        # 5. Now test /analyze/tdoa with 3 receivers (should succeed as Sovereign)
        tdoa_payload = {
            "receivers": [
                {"receiverId": "RX-1", "latitude": 28.6139, "longitude": 77.2090, "timestampUtc": "2026-09-20T00:00:00Z"},
                {"receiverId": "RX-2", "latitude": 28.5355, "longitude": 77.3910, "timestampUtc": "2026-09-20T00:00:00Z"},
                {"receiverId": "RX-3", "latitude": 28.4595, "longitude": 77.0266, "timestampUtc": "2026-09-20T00:00:00Z"},
            ]
        }
        tdoa_res = await client.post(
            "/api/v1/analyze/tdoa",
            json=tdoa_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert tdoa_res.status_code == 200
        assert tdoa_res.json()["data"]["locked"] is False


@pytest.mark.asyncio
async def test_account_lockout_on_failed_logins():
    transport = ASGITransport(app=app)
    unique_email = f"lockout_{uuid.uuid4().hex[:8]}@defense.gov"
    correct_pwd = "CorrectPassword123!"
    wrong_pwd = "WrongPassword999!"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user & verify OTP
        await client.post("/api/v1/auth/register", json={"email": unique_email, "password": correct_pwd})
        await client.post("/api/v1/auth/verify-otp", json={"email": unique_email, "otp": "123456"})

        # Send 5 failed login attempts
        for _ in range(5):
            fail_res = await client.post("/api/v1/auth/login", json={"email": unique_email, "password": wrong_pwd})
            assert fail_res.status_code == 401

        # 6th attempt should be locked out (403 ACCOUNT_LOCKED)
        locked_res = await client.post("/api/v1/auth/login", json={"email": unique_email, "password": wrong_pwd})
        assert locked_res.status_code == 403
        assert locked_res.json()["error"]["code"] == "ACCOUNT_LOCKED"
