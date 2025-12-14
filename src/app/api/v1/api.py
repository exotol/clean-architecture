from fastapi import APIRouter

from app.api.v1.endpoints import rag


def config_routers_endpoints_v1() -> APIRouter:
    router = APIRouter()
    router.include_router(rag.router)
    return router
