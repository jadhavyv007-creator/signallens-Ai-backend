"""
File Storage and Retrieval Service.
Provides local private file storage and signed URL generation.
"""

import os
import uuid
from typing import Tuple, Optional
from api.schemas.common import APIException

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "signal-files")


class StorageService:
    def __init__(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    def save_file(self, content: bytes, original_name: str, user_id: Optional[str] = None) -> str:
        prefix = user_id if user_id else "anon"
        file_id = uuid.uuid4().hex[:12]
        safe_name = "".join(c for c in original_name if c.isalnum() or c in (".", "_", "-"))
        rel_path = f"{prefix}/{file_id}_{safe_name}"
        full_path = os.path.join(STORAGE_DIR, rel_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(content)
        return rel_path

    def get_file_bytes(self, storage_path: str) -> bytes:
        # Prevent path traversal
        clean_path = os.path.normpath(storage_path).lstrip("/")
        full_path = os.path.join(STORAGE_DIR, clean_path)
        if not os.path.exists(full_path) or not full_path.startswith(STORAGE_DIR):
            raise APIException(status_code=404, code="FILE_NOT_FOUND", message="Requested signal capture file not found")
        with open(full_path, "rb") as f:
            return f.read()

    def generate_signed_url(self, storage_path: str, expiration_seconds: int = 3600) -> str:
        clean_path = storage_path.lstrip("/")
        return f"/api/v1/files/{clean_path}?expires_in={expiration_seconds}"
