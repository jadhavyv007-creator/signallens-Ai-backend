"""
DSP Pipeline Execution Service with Tier Size and Format Gating.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from api.config.env import env
from api.database.models import UserModel
from api.database.repositories import AnalysisRepository
from api.schemas.common import APIException
from signalens.loaders import load_signal
from signalens.analysis import analyze_signal_full

MAX_MB_PER_TIER = {
    "base": 25,
    "cyber_pro": 500,
    "sovereign": 8192,
}

FORMATS_PER_TIER = {
    "base": [".wav", ".ogg", ".oga"],
    "cyber_pro": [".wav", ".ogg", ".oga", ".iq", ".raw", ".bin", ".dat", ".cf32", ".cs16"],
    "sovereign": [".wav", ".ogg", ".oga", ".iq", ".raw", ".bin", ".dat", ".cf32", ".cs16"],
}


class DSPService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.analysis_repo = AnalysisRepository(db) if db else None

    def validate_tier_limits(self, file_name: str, file_size_bytes: int, tier: str) -> None:
        tier_key = tier.lower() if tier.lower() in MAX_MB_PER_TIER else "base"
        max_mb = MAX_MB_PER_TIER.get(tier_key, 25)
        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb > max_mb:
            raise APIException(
                status_code=402,
                code="TIER_LIMIT_EXCEEDED",
                message=f"File size ({file_size_mb:.1f} MB) exceeds your {tier.upper()} tier limit of {max_mb} MB. Upgrade tier to upload larger captures.",
            )

        # Format check
        ext = "." + file_name.split(".")[-1].lower() if "." in file_name else ""
        allowed_exts = FORMATS_PER_TIER.get(tier_key, [".wav", ".ogg", ".oga"])
        if ext and ext not in allowed_exts and tier_key == "base":
            raise APIException(
                status_code=403,
                code="FEATURE_LOCKED",
                message=f"Raw SDR binary captures ({ext}) require Cyber Pro or Sovereign tier. Base tier supports .WAV and .OGG.",
            )

    async def run_analysis(
        self,
        file_bytes: bytes,
        file_name: str,
        user: Optional[UserModel] = None,
        sample_rate: int = 44100,
        iq_dtype: str = "uint8",
        carrier_freq_hz: Optional[float] = None,
    ) -> Dict[str, Any]:
        tier = user.tier if user else "base"
        file_size = len(file_bytes)

        # 1. Validate Tier Limits
        self.validate_tier_limits(file_name, file_size, tier)

        # 2. Decode Signal
        try:
            signal_data, sr, is_iq, detected_format = load_signal(
                file_bytes, file_name=file_name, sample_rate=sample_rate, iq_dtype=iq_dtype
            )
        except Exception as e:
            raise APIException(
                status_code=400,
                code="INVALID_SIGNAL_FILE",
                message=f"Failed to decode signal capture: {str(e)}",
            )

        # 3. Execute Pure-NumPy Analysis Pipeline
        result = analyze_signal_full(
            signal=signal_data,
            sample_rate=sr,
            file_name=file_name,
            file_size_bytes=file_size,
            detected_format=detected_format,
            is_iq=is_iq,
            tier=tier,
            carrier_freq_hz=carrier_freq_hz,
        )

        # 4. Optional Persistence to DB if authenticated and db session provided
        if self.analysis_repo and user:
            try:
                await self.analysis_repo.create(
                    user_id=user.id,
                    file_name=file_name,
                    predicted_class=result["aiAnalysis"]["predictedClass"],
                    confidence=result["aiAnalysis"]["confidence"],
                    is_anomaly=result["aiAnalysis"]["isAnomaly"],
                    anomaly_score=result["aiAnalysis"]["anomalyScore"],
                    report_text=result["report"],
                    metrics_json=result["metrics"],
                    advanced_json=result["advanced"],
                )
            except Exception as e:
                print(f"⚠️ Non-fatal DB persistence warning: {e}")

        return result
