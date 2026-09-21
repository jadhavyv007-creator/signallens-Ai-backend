"""
SignalLens AI - FastAPI Application Entrypoint.
Conforms strictly to instruction.md and SignallensAI_prd.md standards.
"""

import os
import sys

# Ensure repository root and api directory are on sys.path in serverless runtime
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_current_dir)
for _p in [_current_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config.env import env

from api.database.db import init_db
from api.middleware.error_handler import (
    api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from api.middleware.security import SecurityHeadersMiddleware
from api.middleware.rate_limit import RateLimiterMiddleware
from api.middleware.json_sanitizer import JsonSanitizerMiddleware
from api.schemas.common import APIException
from api.routes import (
    health_router,
    auth_router,
    analyze_router,
    billing_router,
    files_router,
    payments_router,
)
from signalens.analysis import get_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    print(f"🚀 Initializing SignalLens AI Backend ({env.NODE_ENV} mode)...")
    
    # 1. Initialize DB tables safely
    try:
        await init_db()
        print("✅ Database schema synchronized.")
    except Exception as e:
        print(f"⚠️ DB startup warning: {e}")
    
    # 2. Pre-load pure-NumPy Random Forest model into memory
    try:
        model = get_model()
        print(f"🌲 DSP Random Forest model preloaded ({model.n_estimators} trees, classes: {', '.join(model.classes)}).")
    except Exception as e:
        print(f"⚠️ Model startup warning: {e}")
    
    yield
    
    # ── Shutdown ─────────────────────────────────────────────────────────
    print("🛑 SignalLens AI Backend shutting down gracefully.")


import os

is_serverless = bool(
    os.environ.get("VERCEL")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or os.environ.get("LAMBDA_TASK_ROOT")
)

app = FastAPI(
    title="SignalLens AI Backend",
    description="Automated Signal Intelligence (SIGINT) & Pure-NumPy DSP Workbench API",
    version="3.0.0",
    lifespan=None if is_serverless else lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# 1. Exception Handlers (Standard Error Response Shape)
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 2. Security Headers & Payload Sanitization
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(JsonSanitizerMiddleware)

# 3. Rate Limiting
app.add_middleware(RateLimiterMiddleware)

# 4. CORS Middleware — explicit allowlist only
app.add_middleware(
    CORSMiddleware,
    allow_origins=env.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# 5. Route Mounts
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(billing_router)
app.include_router(files_router)
app.include_router(payments_router)


@app.get("/", summary="Root status check")
async def root():
    return {
        "success": True,
        "data": {
            "name": "SignalLens AI Enterprise SIGINT API",
            "version": "3.0.0",
            "status": "online",
            "docs": "/docs" if env.NODE_ENV != "production" else None,
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=env.HOST, port=env.PORT, reload=env.DEBUG)
