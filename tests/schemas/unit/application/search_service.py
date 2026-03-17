from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


if TYPE_CHECKING:
    from app.domain.entities.document import Document


class SearchServiceEntity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    mock_return: list[Document] = Field(default_factory=list)
    mock_side_effect: Exception | None = None


class SearchServiceExpected(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    count: int = 0
    results: list[Document] = Field(default_factory=list)
    expected_exception: type[Exception] | None = None
