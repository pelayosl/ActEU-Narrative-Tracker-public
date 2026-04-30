from fastapi import APIRouter, Depends

from app.schemas.topic import Topic
from app.services.topic_modelling_service import TopicModellingService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/generate")
async def generate_topics(
    doc_ids: list[str],
    service: TopicModellingService = Depends(),
) -> dict:
    raise NotImplementedError


@router.post("/reconcile")
async def reconcile_topics(
    topics: list[Topic],
    service: TopicModellingService = Depends(),
) -> dict:
    raise NotImplementedError
