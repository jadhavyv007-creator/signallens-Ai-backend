"""
File Download and URL Generation Routes.
"""

from fastapi import APIRouter, Depends, Response, Query
from fastapi.responses import Response as RawResponse
from api.middleware.auth_guard import get_current_user_optional
from api.services.storage_service import StorageService
from api.schemas.common import APIResponse

router = APIRouter(prefix="/api/v1/files", tags=["Files"])


@router.get("/{storage_path:path}/url", response_model=APIResponse[dict])
async def get_file_signed_url(
    storage_path: str,
    expires_in: int = Query(default=3600, ge=60, le=86400),
):
    """Generates a signed URL for a stored signal capture."""
    storage = StorageService()
    url = storage.generate_signed_url(storage_path, expiration_seconds=expires_in)
    return APIResponse(data={"storagePath": storage_path, "downloadUrl": url, "expiresIn": expires_in})


@router.get("/{storage_path:path}")
async def download_file(
    storage_path: str,
):
    """Streams the raw binary / audio file contents."""
    storage = StorageService()
    content = storage.get_file_bytes(storage_path)
    media_type = "audio/wav" if storage_path.endswith(".wav") else "application/octet-stream"
    return RawResponse(content=content, media_type=media_type)
