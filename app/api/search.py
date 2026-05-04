from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_service
from app.schemas.search import SearchQuery, SearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResult)
async def search(
    query: SearchQuery,
    service: SearchService = Depends(get_search_service),
) -> SearchResult:
    raise NotImplementedError
