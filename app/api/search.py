from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_search_service
from app.schemas.auth import User
from app.schemas.search import SearchQuery, SearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/")
async def search(
    query: SearchQuery,
    service: Annotated[SearchService, Depends(get_search_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> SearchResult:
    return await service.search(query)


@router.post("/by-ids")
async def get_documents_by_ids(
    doc_ids: list[str],
    service: Annotated[SearchService, Depends(get_search_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    return await service.get_documents_by_ids(doc_ids)
