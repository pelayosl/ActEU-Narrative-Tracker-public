from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_current_user,
    get_project_service,
    get_visualisation_service,
)
from app.exceptions import ProjectAccessDenied, ProjectNotFound
from app.schemas.auth import User
from app.schemas.visualisation import Dashboard, VisualisationQuery
from app.services.project_service import ProjectService
from app.services.visualisation_service import VisualisationService

router = APIRouter(prefix="/visualisation", tags=["visualisation"])


@router.post("/")
async def load_dashboard(
    query: VisualisationQuery,
    service: Annotated[VisualisationService, Depends(get_visualisation_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[str | None, Query()] = None,
) -> Dashboard:
    if project_id:
        try:
            await project_service.verify_project_owner(project_id, current_user.user_id)
        except ProjectNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        except ProjectAccessDenied:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await service.load_dashboard(query, project_id)
