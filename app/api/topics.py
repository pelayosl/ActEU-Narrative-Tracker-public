from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_project_service,
    get_topic_modelling_service,
)
from app.exceptions import ProjectAccessDenied, ProjectNotFound
from app.schemas.auth import User
from app.schemas.topic import GenerateTopicsRequest, ReconciliationRequest
from app.services.project_service import ProjectService
from app.services.topic_modelling_service import TopicModellingService

router = APIRouter(prefix="/topics", tags=["topics"])

P_NOT_FOUND = "Project not found"
ACCESS_DENIED = "Access denied"


@router.post("/generate")
async def generate_topics(
    body: GenerateTopicsRequest,
    service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        await project_service.verify_project_owner(body.project_id, current_user.user_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)

    job_id = service.submit_generation(body.project_id, body.doc_ids)
    return {"job_id": job_id}


@router.post("/reconcile")
async def reconcile_topics(
    body: ReconciliationRequest,
    service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        await project_service.verify_project_owner(body.project_id, current_user.user_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)

    job_id = service.submit_reconciliation(
        body.project_id,
        [t.model_dump() for t in body.topics],
        [t.model_dump() for t in body.passthrough_topics],
    )
    return {"job_id": job_id}
