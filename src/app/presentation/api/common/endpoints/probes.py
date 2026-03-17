from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from typing import cast

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import JSONResponse

from app.presentation.api.schemas.healthcheck import Liveness
from app.presentation.api.schemas.healthcheck import Readiness


if TYPE_CHECKING:
    from app.domain.interfaces.readiness import IReadinessChecker


router = APIRouter()


@router.get(
    "/live",
    tags=["probes"],
    status_code=HTTPStatus.OK,
    response_model=Liveness,
)
def liveness() -> Liveness:
    """Liveness probe: process is running. No dependency checks."""
    return Liveness()


def get_readiness_checker(request: Request) -> IReadinessChecker:
    """Provide readiness checker from app state (overrideable in tests)."""
    return cast(
        "IReadinessChecker",
        request.app.state.container.readiness_checker(),
    )


@router.get(
    "/ready",
    tags=["probes"],
    response_model=Readiness,
)
async def readiness(
    checker: IReadinessChecker = Depends(get_readiness_checker),
) -> Readiness | JSONResponse:
    """Readiness probe: ready to accept traffic (dependencies OK)."""
    if await checker.is_ready():
        return Readiness()
    return JSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        content=Readiness(status="not_ready").model_dump(),
    )
