"""
Health and Readiness Probes.
Follows instruction.md standards: cheap /health for liveness, /ready for DB connectivity.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from api.database.db import check_db_health

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
@router.get("/live", summary="Liveness probe alias")
async def health_check():
    """Returns 200 if the server process is alive."""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "SignalLens AI Backend",
            "version": "3.0.0",
        }
    }


@router.get("/ready", summary="Readiness probe")
async def readiness_check():
    """Returns 200 only if database connectivity is operational; otherwise 503."""
    db_ok = await check_db_health()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Database connection is not ready",
                }
            }
        )
    return {
        "success": True,
        "data": {
            "status": "ready",
            "database": "connected",
        }
    }
