from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_topic_modelling_service
from app.schemas.auth import User
from app.schemas.topic import GenerateTopicsRequest, ReconciliationRequest
from app.services.topic_modelling_service import TopicModellingService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/generate")
async def generate_topics(
    body: GenerateTopicsRequest,
    service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    job_id = service.submit_generation(body.project_id, body.doc_ids)
    return {"job_id": job_id}


@router.post("/reconcile")
async def reconcile_topics(
    body: ReconciliationRequest,
    service: Annotated[TopicModellingService, Depends(get_topic_modelling_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    job_id = service.submit_reconciliation(body.project_id, [t.model_dump() for t in body.topics])
    return {"job_id": job_id}
