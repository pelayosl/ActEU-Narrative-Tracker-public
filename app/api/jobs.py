from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_job_queue
from app.infrastructure.job_queue_service import JobQueueService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_queue: JobQueueService = Depends(get_job_queue),
) -> EventSourceResponse:
    raise NotImplementedError
