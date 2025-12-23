from fastapi import APIRouter

from app.presentation.api.v1.endpoints import search


def config_routers_endpoints_v1() -> APIRouter:
    router = APIRouter()
    router.include_router(search.router)
    return router
