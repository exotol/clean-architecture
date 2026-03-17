from __future__ import annotations

from fastapi import APIRouter

from app.core.constants import HELLO_WORLD
from app.presentation.api.schemas.root import HelloWorld


router = APIRouter()


@router.get(
    "/",
    tags=["root"],
    response_model=HelloWorld,
)
def root() -> HelloWorld:
    """Root endpoint."""
    return HelloWorld(message=HELLO_WORLD)
