from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import APIRouter
from fastapi import Depends

from app.core.containers import AppContainer
from app.presentation.api.schemas.search import Document
from app.presentation.api.schemas.search import SearchRequest
from app.presentation.api.schemas.search import SearchResponse


if TYPE_CHECKING:
    from app.application.services.search_service import SearchService


router = APIRouter()


@router.post("/answer/generate", tags=["rag"])
@inject
async def generate_answer(
    request: SearchRequest,
    search_service: SearchService = Depends(
        Provide[AppContainer.search_service],
    ),
) -> SearchResponse:
    """Generate an answer for the request using the search service."""
    documents = await search_service.search(query=request.query)

    # Mapper Logic (Domain Entity -> Schema)
    return SearchResponse(
        documents=[
            Document(text=doc.text, metadata=doc.metadata) for doc in documents
        ],
    )
