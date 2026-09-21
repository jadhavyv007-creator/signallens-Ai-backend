"""
Integration tests for FastAPI endpoints (/health, /ready, /analyze, /analyze/tdoa).
"""

import io
import wave
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport
from api.main import app


def create_synthetic_wav_bytes(duration_sec: float = 0.2, freq_hz: float = 1000.0) -> bytes:
    sample_rate = 44100
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, n_samples)
    data = (np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health
        res = await client.get("/health")
        assert res.status_code == 200
        json_data = res.json()
        assert json_data["success"] is True
        assert json_data["data"]["status"] == "healthy"

        # 2. Ready
        res_ready = await client.get("/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["data"]["database"] == "connected"


@pytest.mark.asyncio
async def test_analyze_endpoint_anonymous_base_tier():
    transport = ASGITransport(app=app)
    wav_bytes = create_synthetic_wav_bytes(duration_sec=0.1, freq_hz=800.0)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("test_signal.wav", wav_bytes, "audio/wav")}
        data = {"sample_rate": "44100", "carrier_freq_hz": "100000000"}

        res = await client.post("/api/v1/analyze", files=files, data=data)
        assert res.status_code == 200
        json_res = res.json()
        assert json_res["success"] is True

        payload = json_res["data"]
        assert "metrics" in payload
        assert "visualizations" in payload
        assert "aiAnalysis" in payload
        assert "advanced" in payload

        # Base tier has locked Pro and Sovereign features
        assert payload["advanced"]["fingerprint"]["locked"] is True
        assert payload["advanced"]["fingerprint"]["requiredTier"] == "CYBER_PRO"
        assert payload["advanced"]["bss"]["locked"] is True
        assert payload["advanced"]["bss"]["requiredTier"] == "SOVEREIGN"


@pytest.mark.asyncio
async def test_analyze_tdoa_insufficient_receivers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First register sovereign user or test unauthorized
        # Anonymous should return 401
        payload = {
            "receivers": [
                {"receiverId": "RX-1", "latitude": 28.0, "longitude": 77.0, "timestampUtc": "2026-09-20T00:00:00Z"},
                {"receiverId": "RX-2", "latitude": 28.1, "longitude": 77.1, "timestampUtc": "2026-09-20T00:00:00Z"},
            ]
        }
        res = await client.post("/api/v1/analyze/tdoa", json=payload)
        assert res.status_code in (401, 403)
