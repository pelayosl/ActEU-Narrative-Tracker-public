from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_project_service, get_search_service
from app.exceptions import ProjectAccessDenied, ProjectNotFound
from app.schemas.auth import User
from app.schemas.search import SearchQuery, SearchResult
from app.services.project_service import ProjectService
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/")
async def search(
    query: SearchQuery,
    service: Annotated[SearchService, Depends(get_search_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[str | None, Query(default=None)] = None,
) -> SearchResult:
    result = await service.search(query)

    if query.subtopics and project_id:
        try:
            await project_service.verify_project_owner(project_id, current_user.user_id)
        except ProjectNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        except ProjectAccessDenied:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        doc_ids = [doc.doc_id for doc in result.retrieved_docs]
        filtered_ids = set(
            await project_service.filter_proxies_by_subtopics(project_id, doc_ids, query.subtopics)
        )
        result = SearchResult(
            total_docs=len(filtered_ids),
            retrieved_docs=[doc for doc in result.retrieved_docs if doc.doc_id in filtered_ids],
        )

    return result


@router.post("/by-ids")
async def get_documents_by_ids(
    doc_ids: list[str],
    service: Annotated[SearchService, Depends(get_search_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    return await service.get_documents_by_ids(doc_ids)
