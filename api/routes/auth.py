"""
Authentication and User Profile Endpoints.
Implements HttpOnly Secure SameSite=Strict cookie refresh tokens and token rotation per instruction.md.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.database.db import get_db
from api.database.models import UserModel
from api.services.auth_service import AuthService
from api.middleware.auth_guard import get_current_user
from api.schemas.common import APIResponse
from api.schemas.auth import (
    RegisterRequest,
    RegisterInitiateResponse,
    VerifyOTPRequest,
    LoginRequest,
    TokenResponse,
    UserProfile,
)

router = APIRouter(prefix="/api/v1", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refreshToken"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        secure=True,
        samesite="strict",
    )


@router.post("/auth/register", response_model=APIResponse[RegisterInitiateResponse], status_code=status.HTTP_200_OK)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initiates user registration and triggers Supabase 6-digit email confirmation code."""
    service = AuthService(db)
    res = await service.register(email=body.email, password=body.password, name=body.name)
    return APIResponse(data=RegisterInitiateResponse(message=res["message"], email=res["email"]))


@router.post("/auth/verify-otp", response_model=APIResponse[TokenResponse], status_code=status.HTTP_200_OK)
async def verify_otp(
    body: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Verifies 6-digit email OTP, creates local user profile, and returns Access Token + Refresh Cookie."""
    service = AuthService(db)
    token_resp, raw_refresh = await service.verify_otp(email=body.email, otp=body.otp, name=body.name)
    set_refresh_cookie(response, raw_refresh)
    return APIResponse(data=token_resp)


@router.post("/auth/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    token_resp, raw_refresh = await service.login(email=body.email, password=body.password)
    set_refresh_cookie(response, raw_refresh)
    return APIResponse(data=token_resp)


@router.post("/auth/refresh", response_model=APIResponse[TokenResponse])
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    service = AuthService(db)
    token_resp, new_refresh = await service.refresh_session(refresh_token)
    set_refresh_cookie(response, new_refresh)
    return APIResponse(data=token_resp)


@router.post("/auth/logout", response_model=APIResponse[dict])
async def logout(
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout(current_user.id)
    clear_refresh_cookie(response)
    return APIResponse(data={"loggedOut": True, "message": "Successfully logged out and session revoked."})


@router.get("/users/me", response_model=APIResponse[UserProfile])
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user),
):
    profile = UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tier=current_user.tier,
        createdAt=current_user.created_at,
        updatedAt=current_user.updated_at,
    )
    return APIResponse(data=profile)
