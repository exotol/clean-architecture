from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.common.endpoints import healthcheck
from app.presentation.api.common.endpoints import metrics
from app.presentation.api.common.endpoints import probes
from app.presentation.api.common.endpoints import root


def common_endpoints() -> APIRouter:
    """Create router for common endpoints."""
    router = APIRouter()
    router.include_router(healthcheck.router)
    router.include_router(metrics.router)
    router.include_router(probes.router)
    router.include_router(root.router)
    return router
