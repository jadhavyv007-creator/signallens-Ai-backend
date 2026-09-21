from .health import router as health_router
from .auth import router as auth_router
from .analyze import router as analyze_router
from .billing import router as billing_router
from .files import router as files_router
from .payments import router as payments_router

__all__ = [
    "health_router",
    "auth_router",
    "analyze_router",
    "billing_router",
    "files_router",
    "payments_router",
]
