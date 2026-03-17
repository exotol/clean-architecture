from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel


if TYPE_CHECKING:
    from app.presentation.api.schemas.root import HelloWorld


class RootEntity(BaseModel):
    path: str


class RootExpected(BaseModel):
    status_code: int
    json_body: HelloWorld
