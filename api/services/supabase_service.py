"""
Supabase Authentication Service.
Provides enterprise authentication integration with Supabase GoTrue Auth API.
"""

from typing import Dict, Any, Optional
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError
from api.config.env import env
from api.schemas.common import APIException


class SupabaseAuthService:
    def __init__(self):
        if not env.is_supabase_configured:
            raise APIException(
                status_code=503,
                code="SUPABASE_NOT_CONFIGURED",
                message="Supabase authentication is not configured in environment variables.",
            )
        self.client: Client = create_client(
            supabase_url=env.SUPABASE_URL,
            supabase_key=env.SUPABASE_ANON_KEY,
        )
        self.admin_client: Optional[Client] = None
        if env.SUPABASE_SERVICE_ROLE_KEY and not env.SUPABASE_SERVICE_ROLE_KEY.startswith("your_"):
            try:
                self.admin_client = create_client(
                    supabase_url=env.SUPABASE_URL,
                    supabase_key=env.SUPABASE_SERVICE_ROLE_KEY,
                )
            except Exception:
                self.admin_client = None

    def sign_up(self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Triggers email registration in Supabase Auth to send 6-digit confirmation OTP."""
        try:
            credentials: Dict[str, Any] = {
                "email": email,
                "password": password,
            }
            if metadata:
                credentials["options"] = {"data": metadata}

            response = self.client.auth.sign_up(credentials)
            user = response.user
            if not user:
                raise APIException(
                    status_code=400,
                    code="REGISTRATION_FAILED",
                    message="Failed to register user in Supabase.",
                )
                
            return {
                "user": user,
                "email": email,
            }
        except AuthApiError as e:
            status_code = getattr(e, "status", 400)
            msg = getattr(e, "message", str(e))
            if "already registered" in msg.lower() or status_code == 422:
                raise APIException(
                    status_code=409,
                    code="CONFLICT",
                    message="An account with this email address already exists.",
                )
            if "rate limit" in msg.lower() or status_code == 429:
                raise APIException(
                    status_code=429,
                    code="RATE_LIMIT_EXCEEDED",
                    message="Supabase email rate limit exceeded. Please try again later.",
                )
            raise APIException(
                status_code=status_code or 400,
                code="AUTH_ERROR",
                message=msg,
            )
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                status_code=503,
                code="SUPABASE_UNAVAILABLE",
                message=f"Supabase service unreachable: {str(e)}",
            )

    def verify_otp(self, email: str, token: str, otp_type: str = "signup") -> Dict[str, Any]:
        """Verifies 6-digit OTP code sent to user email."""
        try:
            response = self.client.auth.verify_otp({
                "email": email,
                "token": token.strip(),
                "type": otp_type,
            })
            user = response.user
            session = response.session
            
            if not user:
                raise APIException(
                    status_code=400,
                    code="INVALID_OTP",
                    message="Invalid or expired OTP",
                )
                
            return {
                "user": user,
                "session": session,
                "access_token": getattr(session, "access_token", None),
                "refresh_token": getattr(session, "refresh_token", None),
            }
        except AuthApiError:
            raise APIException(
                status_code=400,
                code="INVALID_OTP",
                message="Invalid or expired OTP",
            )
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                status_code=503,
                code="SUPABASE_UNAVAILABLE",
                message=f"Supabase verification unreachable: {str(e)}",
            )

    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates user with email and password via Supabase Auth."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            
            user = response.user
            session = response.session
            
            if not session or not user:
                raise APIException(
                    status_code=401,
                    code="UNAUTHORIZED",
                    message="Invalid email or password.",
                )
                
            return {
                "user": user,
                "session": session,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in or 3600,
            }
        except AuthApiError as e:
            msg = getattr(e, "message", str(e))
            if "email not confirmed" in msg.lower():
                raise APIException(
                    status_code=403,
                    code="EMAIL_NOT_CONFIRMED",
                    message="Email address has not been confirmed. Please check your inbox or disable 'Confirm email' in Supabase Auth settings.",
                )
            raise APIException(
                status_code=401,
                code="UNAUTHORIZED",
                message="Invalid email or password.",
            )
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                status_code=503,
                code="SUPABASE_UNAVAILABLE",
                message=f"Supabase login unreachable: {str(e)}",
            )

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes active session with Supabase using refresh token."""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            user = response.user
            session = response.session
            
            if not session or not user:
                raise APIException(
                    status_code=401,
                    code="REFRESH_TOKEN_INVALID",
                    message="Supabase session could not be refreshed.",
                )
                
            return {
                "user": user,
                "session": session,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in or 3600,
            }
        except AuthApiError as e:
            raise APIException(
                status_code=401,
                code="REFRESH_TOKEN_INVALID",
                message="Refresh token expired or invalid.",
            )
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                status_code=503,
                code="SUPABASE_UNAVAILABLE",
                message=f"Supabase session refresh unreachable: {str(e)}",
            )

    def get_user_by_token(self, access_token: str) -> Dict[str, Any]:
        """Fetches and validates user profile from Supabase using JWT token."""
        try:
            response = self.client.auth.get_user(access_token)
            if not response or not response.user:
                raise APIException(status_code=401, code="UNAUTHORIZED", message="Invalid Supabase token.")
            return {"user": response.user}
        except Exception as e:
            raise APIException(status_code=401, code="UNAUTHORIZED", message="Invalid or expired Supabase token.")

    def sign_out(self, access_token: Optional[str] = None) -> None:
        """Signs out user from Supabase."""
        try:
            self.client.auth.sign_out()
        except Exception:
            pass
