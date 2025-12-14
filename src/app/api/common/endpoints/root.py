from fastapi import APIRouter

from app.core.constants import HELLO_WORLD
from app.schemas.endpoints.root import HelloWorld

router = APIRouter()


@router.get(
    "/",
    tags=["root"],
    response_model=HelloWorld,
)
def root() -> HelloWorld:
    return HelloWorld(message=HELLO_WORLD)
