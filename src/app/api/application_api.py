from fastapi import APIRouter

from app.api.common.api import common_endpoints
from app.api.v1.api import config_routers_endpoints_v1


def add_common_endpoints(router: APIRouter) -> None:
    router.include_router(common_endpoints(), prefix="/common")


def add_endpoints_v1(router: APIRouter) -> None:
    router.include_router(config_routers_endpoints_v1(), prefix="/v1")


def create_main_router() -> APIRouter:
    router = APIRouter()
    add_common_endpoints(router)
    add_endpoints_v1(router)
    return router
