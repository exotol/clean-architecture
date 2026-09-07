from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class SearchRequest(BaseModel):
    """Search request payload."""

    query: str = Field(..., description="Строка поискового запроса")


class Document(BaseModel):
    """Document returned by search."""

    text: str = Field(..., description="Текстовое содержимое документа")
    metadata: dict[str, str | int | float] = Field(
        ...,
        description="Словарь метаданных документа",
    )


class SearchResponse(BaseModel):
    """Search response payload."""

    documents: list[Document] = Field([], description="List of documents")
