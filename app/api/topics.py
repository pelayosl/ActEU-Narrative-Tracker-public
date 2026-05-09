from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_topic_modelling_service
from app.schemas.topic import GenerateTopicsRequest, Topic
from app.services.topic_modelling_service import TopicModellingService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/generate")
async def generate_topics(
    body: GenerateTopicsRequest,
    service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
) -> dict:
    job_id = service.submit_generation(body.doc_ids)
    return {"job_id": job_id}


@router.post("/reconcile")
async def reconcile_topics(
    topics: list[Topic],
    _service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
) -> dict:
    raise NotImplementedError
