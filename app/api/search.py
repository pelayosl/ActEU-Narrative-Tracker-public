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
    project_id: Annotated[str | None, Query()] = None,
) -> SearchResult:
    """Run a faceted document search, optionally scoped to a project.

    When a project scope and subtopics are given, the project's matching proxy doc_ids
    are resolved first and folded into the query as a union source, and the matched
    project-subtopic names are appended to each document's ``relevant_topics``.

    :param query: The faceted search query.
    :param service: The injected search service.
    :param project_service: The injected project service, used for proxy resolution.
    :param current_user: The authenticated user.
    :param project_id: Optional project scope for resolving project subtopics.
    :returns: The :class:`SearchResult`.
    :raises HTTPException: 404 / 403 if a supplied project is missing or not owned.
    """
    # Subtopics can either be in the main document database, or exclusively inside a project
    # proxy_subtopics is used to find whether the selected subtopics are inside a project
    proxy_subtopics: dict[str, list[str]] = {}
    if query.subtopics and project_id:
        try:
            await project_service.verify_project_owner(project_id, current_user.user_id)
        except ProjectNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        except ProjectAccessDenied:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        # Obtain a dictionary mapping query subtopics to document proxies
        # This verifies whether the subtopics are project-exclusive
        proxy_subtopics = await project_service.filter_proxies_by_subtopics(
            project_id, query.subtopics, query.confidence_threshold
        )

    result = await service.search(query, proxy_doc_ids=list(proxy_subtopics))

    # The document query already filters and enriches document-level subtopics; here we
    # append the matched project-level subtopic names to the docs that carry them.
    if proxy_subtopics:
        result = SearchResult(
            total_docs=result.total_docs,
            retrieved_docs=[
                doc.model_copy(update={
                    "relevant_topics": doc.relevant_topics + proxy_subtopics[doc.doc_id]
                })
                if doc.doc_id in proxy_subtopics else doc
                for doc in result.retrieved_docs
            ],
        )

    return result


@router.get("/languages")
async def get_languages(
    service: Annotated[SearchService, Depends(get_search_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[str]:
    """List the languages available as a search facet.

    :param service: The injected search service.
    :param _: The authenticated user, enforced by the dependency.
    :returns: The sorted list of available languages.
    """
    return await service.get_available_languages()
