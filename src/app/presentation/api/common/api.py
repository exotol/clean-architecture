from fastapi import APIRouter

from app.presentation.api.common.endpoints import healthcheck
from app.presentation.api.common.endpoints import metrics
from app.presentation.api.common.endpoints import root


def common_endpoints() -> APIRouter:
    router = APIRouter()
    router.include_router(healthcheck.router)
    router.include_router(metrics.router)
    router.include_router(root.router)
    return router
