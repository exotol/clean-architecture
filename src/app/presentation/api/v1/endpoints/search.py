from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import APIRouter
from fastapi import Depends

from app.application.services.search_service import SearchService
from app.core.containers import AppContainer
from app.presentation.api.schemas.search import Document
from app.presentation.api.schemas.search import SearchRequest
from app.presentation.api.schemas.search import SearchResponse

router = APIRouter()


@router.post("/answer/generate", tags=["rag"])
@inject
async def generate_answer(
    request: SearchRequest,
    search_service: SearchService = Depends(
        Provide[AppContainer.search_service]
    ),
) -> dict[str, SearchResponse]:
    documents = await search_service.search(query=request.query)

    # Mapper Logic (Domain Entity -> Schema)
    response = SearchResponse(
        documents=[
            Document(text=doc.text, metadata=doc.metadata) for doc in documents
        ]
    )
    return {"hello": response}
