"""
Authentication and User Schemas (Pydantic v2 with camelCase aliases).
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Any


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    OPERATOR = "operator"


class UserTier(str, Enum):
    BASE = "base"
    CYBER_PRO = "cyber_pro"
    SOVEREIGN = "sovereign"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    name: Optional[str] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)


class RegisterInitiateResponse(BaseModel):
    message: str = "Verification code sent to your email"
    email: str

    model_config = ConfigDict(populate_by_name=True)


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=8, description="6 to 8-character verification code")
    name: Optional[str] = Field(default=None)

    @field_validator("otp", mode="before")
    @classmethod
    def sanitize_otp(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    model_config = ConfigDict(populate_by_name=True)



class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(populate_by_name=True)


class UserProfile(BaseModel):
    id: str = Field(alias="id")
    email: str
    name: Optional[str] = None
    role: UserRole = UserRole.USER
    tier: UserTier = UserTier.BASE
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_in: int = Field(default=900, alias="expiresIn")
    user: UserProfile

    model_config = ConfigDict(populate_by_name=True)


class SessionRevokeRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    confirm_text: Optional[str] = Field(default=None, alias="confirmText")

    model_config = ConfigDict(populate_by_name=True)
