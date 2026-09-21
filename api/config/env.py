"""
Environment variable configuration and validation using Pydantic Settings.
Implements the fail-fast startup rule: terminates process immediately if configuration is invalid.
"""

import sys
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NODE_ENV: str = Field(default="development")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    DEBUG: bool = Field(default=False)

    # JWT configuration
    JWT_ACCESS_SECRET: str = Field(min_length=32, default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    JWT_REFRESH_SECRET: str = Field(min_length=32, default="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210")
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
        print("❌ CRITICAL: Invalid environment variables on startup!", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)


env = load_settings()
