from http import HTTPStatus

from fastapi import APIRouter

from app.presentation.api.schemas.healthcheck import Healthcheck

router = APIRouter()


@router.get(
    "/healthcheck",
    tags=["healthcheck"],
    status_code=HTTPStatus.OK,
    response_model=Healthcheck,
)
def healthcheck() -> Healthcheck:
    return Healthcheck()
