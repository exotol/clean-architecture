from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import APIRouter
from fastapi import Depends

from app.core.containers import AppContainer
from app.presentation.api.schemas.agent import AgentRequest
from app.presentation.api.schemas.agent import AgentResponse


if TYPE_CHECKING:
    from app.application.services.agent_service import AgentService


def create_agent_router() -> APIRouter:
    """Create the agent router without module-level mutable state."""
    router = APIRouter(prefix="/agent", tags=["agent"])
    router.add_api_route(
        "/answer",
        generate_agent_answer,
        methods=["POST"],
        response_model=AgentResponse,
    )
    return router


@inject
async def generate_agent_answer(
    request: AgentRequest,
    agent_service: AgentService = Depends(Provide[AppContainer.agent_service]),
) -> AgentResponse:
    """Execute one independent agent request."""
    result = await agent_service.answer(request.query)
    return AgentResponse(
        answer=result.answer,
        tools_used=list(result.tools_used),
    )
