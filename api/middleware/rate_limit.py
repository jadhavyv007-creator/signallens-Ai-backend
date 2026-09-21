"""
Tier-aware and route-specific rate limiting middleware.
Excludes /health and /ready health checks per instruction.md standards.
"""

import time
from typing import Dict, List, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.responses import JSONResponse
from api.schemas.common import APIException


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # IP / User -> list of timestamps
        self.auth_requests: Dict[str, List[float]] = {}
        self.api_requests: Dict[str, List[float]] = {}
        self.clean_interval = 60.0
        self.last_clean = time.time()

    def _clean_old_records(self, now: float):
        if now - self.last_clean > self.clean_interval:
            cutoff = now - 120.0
            self.auth_requests = {k: [t for t in v if t > cutoff] for k, v in self.auth_requests.items()}
            self.api_requests = {k: [t for t in v if t > cutoff] for k, v in self.api_requests.items()}
            self.last_clean = now

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        path = request.url.path
        
        # Exclude liveness/readiness probes from rate limiting
        if path in ("/health", "/ready", "/docs", "/openapi.json"):
            return await call_next(request)

        now = time.time()
        self._clean_old_records(now)

        client_ip = request.client.host if request.client else "unknown"

        # 1. Strict limit for authentication endpoints (10 requests / 60 seconds)
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
            timestamps = self.auth_requests.setdefault(client_ip, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            self.auth_requests[client_ip] = timestamps
            if len(timestamps) >= 10:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many authentication attempts. Please wait 1 minute.",
                        }
                    }
                )
            self.auth_requests[client_ip].append(now)

        # 2. General API rate limit (120 requests / 60 seconds)
        elif path.startswith("/api/"):
            timestamps = self.api_requests.setdefault(client_ip, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            self.api_requests[client_ip] = timestamps
            if len(timestamps) >= 120:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "API request rate limit exceeded. Please slow down.",
                        }
                    }
                )
            self.api_requests[client_ip].append(now)

        return await call_next(request)
