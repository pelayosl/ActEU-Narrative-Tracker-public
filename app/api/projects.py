import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.dependencies import get_current_user, get_project_service
from app.exceptions import ClassifierNotFound, ProjectAccessDenied, ProjectNotFound
from app.schemas.auth import User
from app.schemas.project import Project
from app.schemas.topic import Topic
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

P_NOT_FOUND="Project not found"
ACCESS_DENIED="Access denied"
CLASSIFIER_NOT_FOUND="Classifier not found"

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    name: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Project:
    return await service.create_project(current_user.user_id, name)


@router.get("")
async def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Project]:
    return await service.list_projects(current_user.user_id)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Project:
    try:
        await service.verify_project_owner(project_id, current_user.user_id)
        return await service.get_project(project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        await service.verify_project_owner(project_id, current_user.user_id)
        await service.delete_project(project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)


@router.get("/{project_id}/classifiers/{classifier_id}/download")
async def download_classifier(
    project_id: str,
    classifier_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    try:
        await service.verify_project_owner(project_id, current_user.user_id)
        classifier = await service.get_classifier(project_id, classifier_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)
    except ClassifierNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CLASSIFIER_NOT_FOUND)

    if not os.path.exists(classifier.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classifier file not found")

    return FileResponse(
        classifier.file_path,
        media_type="application/octet-stream",
        filename=f"{classifier.name}.bin",
    )


@router.delete("/{project_id}/classifiers/{classifier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_classifier(
    project_id: str,
    classifier_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        await service.verify_project_owner(project_id, current_user.user_id)
        await service.delete_classifier(project_id, classifier_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)
    except ClassifierNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CLASSIFIER_NOT_FOUND)


@router.get("/{project_id}/topics")
async def get_available_topics(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Topic]:
    try:
        await service.verify_project_owner(project_id, current_user.user_id)
        return await service.get_available_topics(project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)
