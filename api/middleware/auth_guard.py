"""
Authentication and Authorization guard dependencies for FastAPI endpoints.
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from api.database.db import get_db
from api.database.models import UserModel
from api.database.repositories import UserRepository
from api.utils.security import decode_access_token
from api.schemas.common import APIException
from api.schemas.auth import UserTier


TIER_HIERARCHY = {
    UserTier.BASE.value: 1,
    UserTier.CYBER_PRO.value: 2,
    UserTier.SOVEREIGN.value: 3,
}


async def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserModel]:
    """
    Extracts user from access token if provided; returns None if anonymous.
    Enables anonymous demo requests to default to Base tier.
    """
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        return user
    except JWTError:
        return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """
    Requires a valid access token. Raises standard 401 errors if missing/expired.
    """
    if not token:
        raise APIException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Authentication token is required for this endpoint",
        )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise APIException(
                status_code=401,
                code="TOKEN_INVALID",
                message="Token payload is missing user identifier",
            )
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise APIException(
                status_code=401,
                code="UNAUTHORIZED",
                message="User account no longer exists",
            )
        
        # Check lockout
        if user.lockout_until:
            lockout_time = user.lockout_until if user.lockout_until.tzinfo else user.lockout_until.replace(tzinfo=timezone.utc)
            if lockout_time > datetime.now(timezone.utc):
                raise APIException(
                    status_code=403,
                    code="ACCOUNT_LOCKED",
                    message=f"Account is temporarily locked until {lockout_time.isoformat()}",
                )

        return user
    except JWTError as e:
        if "expired" in str(e).lower():
            raise APIException(
                status_code=401,
                code="TOKEN_EXPIRED",
                message="Access token has expired. Please refresh session.",
            )
        raise APIException(
            status_code=401,
            code="TOKEN_INVALID",
            message="Invalid authentication token signature",
        )


def require_tier(required_tier: UserTier):
    """Factory dependency enforcing a minimum subscription tier."""
    async def tier_checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        user_level = TIER_HIERARCHY.get(user.tier, 1)
        required_level = TIER_HIERARCHY.get(required_tier.value, 1)
        if user_level < required_level:
            raise APIException(
                status_code=403,
                code="FEATURE_LOCKED",
                message=f"This feature requires {required_tier.value.upper()} tier or higher",
            )
        return user
    return tier_checker
