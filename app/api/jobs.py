from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_job_queue
from app.infrastructure.job_queue_service import JobQueueService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
) -> EventSourceResponse:
    """SSE stream for job progress. No auth — the job_id UUID is unguessable and
    acts as the access token, matching the pattern used by the frontend EventSource."""
    async def event_generator():
        async for job_status in job_queue.stream_progress(job_id):
            yield {"data": job_status.model_dump_json()}

    return EventSourceResponse(event_generator())
