from fastapi import APIRouter, Depends

from app.schemas.search import SearchQuery
from app.schemas.topic import Topic
from app.services.classification_service import ClassificationService

router = APIRouter(prefix="/classification", tags=["classification"])


@router.post("/train")
async def train_classifier(
    topics: list[Topic],
    doc_ids: list[str],
    service: ClassificationService = Depends(),
) -> dict:
    raise NotImplementedError


@router.post("/label")
async def label_documents(
    classifier_id: str,
    query: SearchQuery,
    service: ClassificationService = Depends(),
) -> dict:
    raise NotImplementedError
