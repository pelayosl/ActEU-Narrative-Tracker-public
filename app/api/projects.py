from fastapi import APIRouter, Depends

from app.api.dependencies import get_project_service
from app.schemas.project import Project
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=Project, status_code=201)
async def create_project(
    name: str,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    raise NotImplementedError


@router.get("/", response_model=list[Project])
async def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> list[Project]:
    raise NotImplementedError


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    raise NotImplementedError


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> None:
    raise NotImplementedError
