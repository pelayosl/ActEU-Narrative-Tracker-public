from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_classification_service,
    get_current_user,
    get_project_service,
)
from app.exceptions import (
    ClassifierNotFound,
    NoPendingPipeline,
    ProjectAccessDenied,
    ProjectNotFound,
)
from app.schemas.auth import User
from app.schemas.classification import (
    InitialLabelRequest,
    LabelRequest,
    LabellingResult,
    TrainClassifierRequest,
)
from app.services.classification_service import ClassificationService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/classification", tags=["classification"])

P_NOT_FOUND = "Project not found"
ACCESS_DENIED = "Access denied"
CLASSIFIER_NOT_FOUND = "Classifier not found"
NO_PENDING_PIPELINE = "No pending pipeline — initial labelling unavailable"


@router.post("/train")
async def train_classifier(
    body: TrainClassifierRequest,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        await project_service.verify_project_owner(body.project_id, current_user.user_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)

    job_id = service.submit_training(body.topics, body.project_id, body.name)
    return {"job_id": job_id}


@router.post("/label/initial")
async def apply_initial_labels(
    body: InitialLabelRequest,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LabellingResult:
    """Phase 1 labelling: write proxies for the training documents using the classifier's
    topics (no ML inference). Clears the pending pipeline on success."""
    try:
        await project_service.verify_project_owner(body.project_id, current_user.user_id)
        return await project_service.apply_pipeline_labels(body.project_id, body.classifier_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)
    except ClassifierNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CLASSIFIER_NOT_FOUND)
    except NoPendingPipeline:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_PENDING_PIPELINE)


@router.post("/label")
async def label_documents(
    body: LabelRequest,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Phase 2 labelling: dispatch async job that runs a new query, applies the classifier,
    and persists proxies. Returns a job_id (poll via /jobs/{job_id}/stream)."""
    try:
        await project_service.verify_project_owner(body.project_id, current_user.user_id)
        # Verify the classifier exists in this project before dispatching
        await project_service.get_classifier(body.project_id, body.classifier_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=P_NOT_FOUND)
    except ProjectAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED)
    except ClassifierNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CLASSIFIER_NOT_FOUND)

    job_id = service.submit_labelling(body.project_id, body.classifier_id, body.query)
    return {"job_id": job_id}
