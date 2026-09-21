"""
Tests for Supabase Authentication Integration.
"""

from unittest.mock import MagicMock, PropertyMock, patch
import pytest
from api.config.env import Settings
from api.schemas.common import APIException
from api.services.supabase_service import SupabaseAuthService
from api.services.auth_service import AuthService


def test_supabase_service_init_error():
    with patch.object(Settings, "is_supabase_configured", new_callable=PropertyMock, return_value=False):
        with pytest.raises(APIException) as exc_info:
            SupabaseAuthService()
        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "SUPABASE_NOT_CONFIGURED"


def test_supabase_service_methods_mocked():
    mock_client = MagicMock()
    
    # Mock sign_up
    mock_user = MagicMock()
    mock_user.id = "supa-user-uuid-1234"
    mock_session = MagicMock()
    mock_session.access_token = "supa_access_token"
    mock_session.refresh_token = "supa_refresh_token"
    mock_session.expires_in = 3600
    mock_client.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)
    mock_client.auth.sign_in_with_password.return_value = MagicMock(user=mock_user, session=mock_session)
    mock_client.auth.refresh_session.return_value = MagicMock(user=mock_user, session=mock_session)
    mock_client.auth.get_user.return_value = MagicMock(user=mock_user)

    # Initialize service with mock client
    service = SupabaseAuthService.__new__(SupabaseAuthService)
    service.client = mock_client
    service.admin_client = None
    
    # 1. Sign Up (Initiate)
    res_signup = service.sign_up("test@example.com", "Password123!")
    assert res_signup["user"].id == "supa-user-uuid-1234"
    assert res_signup["email"] == "test@example.com"

    # 2. Verify OTP
    mock_client.auth.verify_otp.return_value = MagicMock(user=mock_user, session=mock_session)
    res_verify = service.verify_otp("test@example.com", "123456")
    assert res_verify["user"].id == "supa-user-uuid-1234"
    assert res_verify["access_token"] == "supa_access_token"

    # 3. Sign In
    res_signin = service.sign_in_with_password("test@example.com", "Password123!")
    assert res_signin["user"].id == "supa-user-uuid-1234"

    # 4. Refresh
    res_refresh = service.refresh_session("supa_refresh_token")
    assert res_refresh["user"].id == "supa-user-uuid-1234"

    # 5. Get User
    res_user = service.get_user_by_token("supa_access_token")
    assert res_user["user"].id == "supa-user-uuid-1234"


@pytest.mark.asyncio
async def test_auth_service_with_supabase_integration(async_db_session):
    import uuid
    unique_id = f"supa-uuid-{uuid.uuid4().hex[:8]}"
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.id = unique_id
    mock_user.user_metadata = {"name": "Supabase User"}
    mock_session = MagicMock()
    mock_session.access_token = "supa_access"
    mock_session.refresh_token = "supa_refresh"
    mock_session.expires_in = 3600
    mock_client.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)
    mock_client.auth.verify_otp.return_value = MagicMock(user=mock_user, session=mock_session)
    mock_client.auth.sign_in_with_password.return_value = MagicMock(user=mock_user, session=mock_session)

    mock_supa_service = SupabaseAuthService.__new__(SupabaseAuthService)
    mock_supa_service.client = mock_client
    mock_supa_service.admin_client = None

    unique_email = f"supa_{uuid.uuid4().hex[:8]}@signallens.ai"
    auth_service = AuthService(async_db_session)
    auth_service.supabase = mock_supa_service
    
    # 1. Register (Sends OTP)
    init_resp = await auth_service.register(
        email=unique_email,
        password="SecurePassword123!",
        name="Supabase Analyst"
    )
    assert init_resp["email"] == unique_email
    assert "message" in init_resp

    # 2. Verify OTP (Creates user profile & returns tokens)
    token_resp, refresh_token = await auth_service.verify_otp(
        email=unique_email,
        otp="123456",
        name="Supabase Analyst"
    )
    assert token_resp.user.email == unique_email
    assert token_resp.user.id == unique_id
    assert token_resp.access_token is not None
    
    # 3. Login via Supabase
    login_resp, login_refresh = await auth_service.login(
        email=unique_email,
        password="SecurePassword123!"
    )
    assert login_resp.user.id == unique_id
    assert login_resp.access_token is not None


