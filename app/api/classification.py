from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_classification_service, get_current_user
from app.schemas.auth import User
from app.schemas.classification import TrainClassifierRequest
from app.schemas.search import SearchQuery
from app.services.classification_service import ClassificationService

router = APIRouter(prefix="/classification", tags=["classification"])


@router.post("/train")
async def train_classifier(
    body: TrainClassifierRequest,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    job_id = service.submit_training(body.topics, body.project_id, body.generation_job_id)
    return {"job_id": job_id}


@router.post("/label")
async def label_documents(
    project_id: str,
    classifier_id: str,
    query: SearchQuery,
    service: Annotated[ClassificationService, Depends(get_classification_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    raise NotImplementedError
