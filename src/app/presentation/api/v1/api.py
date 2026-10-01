from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1.endpoints import search
from app.presentation.api.v1.endpoints.agent import create_agent_router


def config_routers_endpoints_v1() -> APIRouter:
    """Configure API v1 routers."""
    router = APIRouter()
    router.include_router(search.router)
    router.include_router(create_agent_router())
    return router
