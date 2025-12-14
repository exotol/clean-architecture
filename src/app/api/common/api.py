from fastapi import APIRouter

from app.api.common.endpoints import healthcheck, root


def common_endpoints() -> APIRouter:
    router = APIRouter()
    router.include_router(healthcheck.router)
    router.include_router(root.router)
    return router
