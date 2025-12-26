from http import HTTPStatus

from fastapi import APIRouter

from app.core.events import Events
from app.core.monitor import monitor
from app.presentation.api.schemas.healthcheck import Healthcheck

router = APIRouter()


@router.get(
    "/healthcheck",
    tags=["healthcheck"],
    status_code=HTTPStatus.OK,
    response_model=Healthcheck,
)
@monitor(Events.HEALTHCHECK)
def healthcheck() -> Healthcheck:
    return Healthcheck()
