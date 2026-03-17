from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class SearchRequest(BaseModel):
    """Search request payload."""

    query: str


class Document(BaseModel):
    """Document returned by search."""

    text: str
    metadata: dict[str, str | int | float]


class SearchResponse(BaseModel):
    """Search response payload."""

    documents: list[Document] = Field([], description="List of documents")
