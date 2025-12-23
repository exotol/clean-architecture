from pydantic import (
    BaseModel,
    Field,
)


class SearchRequest(BaseModel):
    query: str


class Document(BaseModel):
    text: str
    metadata: dict[str, str | int | float]


class SearchResponse(BaseModel):
    documents: list[Document] = Field([], description="List of documents")
