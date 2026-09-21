"""
Environment variable configuration and validation using Pydantic Settings.
Resilient against empty environment strings, type mismatches, and serverless runtime quirks.
"""

import sys
from typing import List, Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NODE_ENV: str = Field(default="development")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    DEBUG: bool = Field(default=False)

    # JWT configuration
    JWT_ACCESS_SECRET: str = Field(default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    JWT_REFRESH_SECRET: str = Field(default="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210")
    JWT_ACCESS_EXPIRES_MINUTES: int = Field(default=15)
    JWT_REFRESH_EXPIRES_DAYS: int = Field(default=7)

    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./signallens.db")

    # Supabase (optional cloud auth & database)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")

    # Tier upload limits (MB)
    TIER_BASE_MAX_UPLOAD_MB: int = Field(default=25)
    TIER_CYBER_PRO_MAX_UPLOAD_MB: int = Field(default=500)
    TIER_SOVEREIGN_MAX_UPLOAD_MB: int = Field(default=8192)

    # Billing & payments
    STRIPE_SECRET_KEY: Optional[str] = "sk_test_mock"
    STRIPE_WEBHOOK_SECRET: Optional[str] = "whsec_mock"
    UPI_PROVIDER_API_KEY: Optional[str] = "upi_test_key"
    VITE_ENABLE_PAYMENT_SIMULATION: bool = Field(default=True)
    ENABLE_MOCK_PAYMENTS: bool = Field(default=True)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    # Monitoring & logging
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("PORT", "JWT_ACCESS_EXPIRES_MINUTES", "JWT_REFRESH_EXPIRES_DAYS", "TIER_BASE_MAX_UPLOAD_MB", "TIER_CYBER_PRO_MAX_UPLOAD_MB", "TIER_SOVEREIGN_MAX_UPLOAD_MB", mode="before")
    @classmethod
    def sanitize_integers(cls, v: Any, info) -> Any:
        if v is None or v == "" or (isinstance(v, str) and not v.strip().isdigit()):
            defaults = {
                "PORT": 8000,
                "JWT_ACCESS_EXPIRES_MINUTES": 15,
                "JWT_REFRESH_EXPIRES_DAYS": 7,
                "TIER_BASE_MAX_UPLOAD_MB": 25,
                "TIER_CYBER_PRO_MAX_UPLOAD_MB": 500,
                "TIER_SOVEREIGN_MAX_UPLOAD_MB": 8192,
            }
            return defaults.get(info.field_name, 0)
        return int(v)

    @field_validator("DEBUG", "VITE_ENABLE_PAYMENT_SIMULATION", "ENABLE_MOCK_PAYMENTS", mode="before")
    @classmethod
    def sanitize_booleans(cls, v: Any, info) -> Any:
        if v is None or v == "":
            defaults = {
                "DEBUG": False,
                "VITE_ENABLE_PAYMENT_SIMULATION": True,
                "ENABLE_MOCK_PAYMENTS": True,
            }
            return defaults.get(info.field_name, False)
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "t")
        return bool(v)

    @field_validator("JWT_ACCESS_SECRET", "JWT_REFRESH_SECRET", mode="before")
    @classmethod
    def sanitize_secrets(cls, v: Any, info) -> str:
        if not v or not isinstance(v, str) or len(v.strip()) < 32:
            defaults = {
                "JWT_ACCESS_SECRET": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "JWT_REFRESH_SECRET": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            }
            return defaults.get(info.field_name, "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        return v.strip()

    @field_validator("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET", "SENTRY_DSN", mode="before")
    @classmethod
    def sanitize_optional_strings(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            val = v.strip()
            return val if val else None
        return str(v)

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_supabase_configured(self) -> bool:
        """Returns True if valid Supabase cloud credentials are configured."""
        return bool(
            self.SUPABASE_URL 
            and self.SUPABASE_ANON_KEY 
            and not self.SUPABASE_URL.startswith("https://your-project")
            and not self.SUPABASE_ANON_KEY.startswith("your_anon")
        )

    @property
    def is_razorpay_configured(self) -> bool:
        """Returns True if valid Razorpay API keys are configured."""
        return bool(
            self.RAZORPAY_KEY_ID
            and self.RAZORPAY_KEY_SECRET
            and not self.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder")
            and not self.RAZORPAY_KEY_SECRET.startswith("rzp_secret_placeholder")
        )

    @property
    def effective_database_url(self) -> str:
        """Returns writable database URL on serverless platforms (Vercel / Lambda)."""
        import os
        is_serverless = bool(
            os.environ.get("VERCEL")
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or os.environ.get("LAMBDA_TASK_ROOT")
        )
        if is_serverless:
            if "sqlite" in self.DATABASE_URL and not self.DATABASE_URL.startswith("sqlite+aiosqlite:////tmp"):
                return "sqlite+aiosqlite:////tmp/signallens.db"
        return self.DATABASE_URL


def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        print(f"⚠️ Warning loading environment variables: {e}", file=sys.stderr)
        try:
            return Settings.model_construct()
        except Exception:
            return Settings()


env = load_settings()

