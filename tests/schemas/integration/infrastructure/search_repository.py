from typing import Any

from pydantic import BaseModel


class SearchRepoEntity(BaseModel):
    query: str


class SearchRepoExpected(BaseModel):
    count: int
    text_part: str
    metadata: dict[str, Any]
