"""
Central exception handler ensuring all errors conform to the standard instruction.md JSON response shape:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "fields": { "field": ["detail"] }
    }
}
"""

from typing import Dict, List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.schemas.common import APIException


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    payload = {
        "success": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }
    if exc.fields:
        payload["error"]["fields"] = exc.fields
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: Dict[str, List[str]] = {}
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", []) if item not in ("body", "query", "path"))
        field_name = loc if loc else "request"
        msg = err.get("msg", "Invalid value")
        fields.setdefault(field_name, []).append(msg)

    payload = {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "fields": fields,
        }
    }
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_map = {
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": str(exc.detail),
        }
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log exception internally
    print(f"❌ Unhandled Server Error on {request.method} {request.url.path}: {exc}")
    payload = {
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected internal server error occurred",
        }
    }
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)
