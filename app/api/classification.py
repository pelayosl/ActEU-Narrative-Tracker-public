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
    PendingPipelineMismatch,
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
PENDING_PIPELINE_MISMATCH = (
    "Pending pipeline no longer belongs to this classifier — initial labelling "
    "unavailable. Use a custom query (Phase 2) instead."
)


@router.post("/train")
async def train_classifier(
    body: TrainClassifierRequest,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Dispatch a classifier-training job for a project.

    :param body: The request with topics, project_id and name.
    :param service: The injected classification service.
    :param project_service: The injected project service, used for the ownership check.
    :param current_user: The authenticated user.
    :returns: A ``{"job_id": ...}`` dict for streaming progress.
    :raises HTTPException: 404 / 403 if the project is missing or not owned.
    """
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
    """Apply Phase 1 labels synchronously from the training-era mapping.

    Writes proxies for the training documents using the classifier's topics with no ML
    inference, and clears the pending pipeline on success.

    :param body: The request with project_id and classifier_id.
    :param project_service: The injected project service.
    :param current_user: The authenticated user.
    :returns: The :class:`LabellingResult` summarising the labels written.
    :raises HTTPException: 404 if the project or classifier is missing, 403 if not
        owned, 409 if there is no pending pipeline or it no longer matches the classifier.
    """
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
    except PendingPipelineMismatch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=PENDING_PIPELINE_MISMATCH
        )


@router.post("/label")
async def label_documents(
    body: LabelRequest,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Dispatch a Phase 2 labelling job for a new query within a project.

    The job runs the query, applies the classifier and persists proxies. Progress is
    polled via ``/jobs/{job_id}/stream``.

    :param body: The request with project_id, classifier_id and query.
    :param service: The injected classification service.
    :param project_service: The injected project service, used for the ownership and
        classifier-existence checks.
    :param current_user: The authenticated user.
    :returns: A ``{"job_id": ...}`` dict for streaming progress.
    :raises HTTPException: 404 if the project or classifier is missing, 403 if not owned.
    """
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
