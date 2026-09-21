"""
Standard API Response shapes and Error definitions conforming to instruction.md standards.
"""

from typing import Generic, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code constant")
    message: str = Field(description="Human-readable error description")
    fields: Optional[Dict[str, List[str]]] = Field(default=None, description="Field-specific validation error details")

    model_config = ConfigDict(populate_by_name=True)


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    model_config = ConfigDict(populate_by_name=True)


class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

    model_config = ConfigDict(populate_by_name=True)


class PaginatedAPIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T] = Field(default_factory=list)
    pagination: PaginationMeta
    error: Optional[ErrorDetail] = None

    model_config = ConfigDict(populate_by_name=True)


class APIException(Exception):
    """Base application exception that maps to standard error JSON structure."""
    def __init__(
        self,
        status_code: int = 400,
        code: str = "BAD_REQUEST",
        message: str = "An error occurred",
        fields: Optional[Dict[str, List[str]]] = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        super().__init__(message)
