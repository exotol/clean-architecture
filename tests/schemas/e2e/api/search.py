from typing import Any

from pydantic import BaseModel


class SearchExpected(BaseModel):
    status_code: int
    text_part: str | None = None


class InvalidSearchEntity(BaseModel):
    payload: dict[str, Any]


class InvalidSearchExpected(BaseModel):
    status_code: int
