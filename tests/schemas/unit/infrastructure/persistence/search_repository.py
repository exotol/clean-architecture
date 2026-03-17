from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SearchRepoEntity(BaseModel):
    """Input: search query."""

    query: str


class SearchRepoExpected(BaseModel):
    """Expected: document count, text part, metadata."""

    count: int
    text_part: str
    metadata: dict[str, Any]
