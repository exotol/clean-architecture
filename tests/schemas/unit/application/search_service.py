from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.domain.entities.document import Document


class SearchServiceEntity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    mock_return: list[Document] = Field(default_factory=list)


class SearchServiceExpected(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    count: int
    results: list[Document] = Field(default_factory=list)
