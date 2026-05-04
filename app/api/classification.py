from fastapi import APIRouter, Depends

from app.api.dependencies import get_classification_service
from app.schemas.search import SearchQuery
from app.schemas.topic import Topic
from app.services.classification_service import ClassificationService

router = APIRouter(prefix="/classification", tags=["classification"])


@router.post("/train")
async def train_classifier(
    topics: list[Topic],
    doc_ids: list[str],
    project_id: str,
    service: ClassificationService = Depends(get_classification_service),
) -> dict:
    raise NotImplementedError


@router.post("/label")
async def label_documents(
    project_id: str,
    classifier_id: str,
    query: SearchQuery,
    service: ClassificationService = Depends(get_classification_service),
) -> dict:
    raise NotImplementedError
