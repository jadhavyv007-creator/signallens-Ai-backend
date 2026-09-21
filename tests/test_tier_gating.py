"""
Tests for Commercial Tier Gating, Upload Caps, and Format Restrictions.
"""

import io
import wave
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from tests.test_api_endpoints import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_format_gating_base_vs_pro():
    transport = ASGITransport(app=app)
    # 1. Anonymous / Base user uploading a .raw binary file -> should be 403 FEATURE_LOCKED
    raw_bytes = b"\x80\x80\x81\x7f" * 100
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("capture.raw", raw_bytes, "application/octet-stream")}
        res = await client.post("/api/v1/analyze", files=files)
        assert res.status_code == 403
        err = res.json()["error"]
        assert err["code"] == "FEATURE_LOCKED"
        assert "Cyber Pro" in err["message"]


@pytest.mark.asyncio
async def test_doppler_velocity_null_without_carrier_freq():
    transport = ASGITransport(app=app)
    wav_bytes = create_synthetic_wav_bytes(duration_sec=0.1, freq_hz=1200.0)

    unique_email = f"pro_doppler_{uuid.uuid4().hex[:8]}@test.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register pro user & verify OTP
        await client.post("/api/v1/auth/register", json={"email": unique_email, "password": "Password123!"})
        verify_res = await client.post("/api/v1/auth/verify-otp", json={"email": unique_email, "otp": "123456"})
        token = verify_res.json()["data"]["accessToken"]

        # Upgrade to Cyber Pro
        await client.post(
            "/api/v1/billing/checkout",
            json={"tier": "cyber_pro", "currency": "INR", "paymentProvider": "simulation"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # 1. Analyze without carrier_freq_hz
        files = {"file": ("sat_pass.wav", wav_bytes, "audio/wav")}
        res1 = await client.post("/api/v1/analyze", files=files, headers={"Authorization": f"Bearer {token}"})
        assert res1.status_code == 200
        doppler_data1 = res1.json()["data"]["advanced"]["doppler"]
        assert doppler_data1["locked"] is False
        assert doppler_data1["estimatedVelocityKmPerSec"] is None
        assert "carrierFreqHz" in doppler_data1["note"]

        # 2. Analyze with carrier_freq_hz = 435000000 (435 MHz UHF)
        res2 = await client.post(
            "/api/v1/analyze",
            files={"file": ("sat_pass.wav", wav_bytes, "audio/wav")},
            data={"carrier_freq_hz": "435000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 200
        doppler_data2 = res2.json()["data"]["advanced"]["doppler"]
        assert doppler_data2["locked"] is False
        assert doppler_data2["estimatedVelocityKmPerSec"] is not None
