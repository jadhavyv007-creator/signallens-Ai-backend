"""
Vercel Serverless Entrypoint for SignalLens AI.
"""

import os
import sys
import traceback

# Ensure repository root and api directory are on sys.path in serverless runtime
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

for p in [ROOT_DIR, CURRENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from api.main import app
except Exception as e:
    tb = traceback.format_exc()
    print("🔥 CRITICAL STARTUP ERROR IN VERCEL:", tb)
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="SignalLens AI - Startup Error Handler")
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def catch_all(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "STARTUP_EXCEPTION",
                    "message": str(e),
                    "traceback": tb.split("\n"),
                }
            }
        )

__all__ = ["app"]



