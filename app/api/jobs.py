from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.infrastructure.job_queue_service import JobQueueService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_queue: JobQueueService = Depends(),
) -> EventSourceResponse:
    raise NotImplementedError
