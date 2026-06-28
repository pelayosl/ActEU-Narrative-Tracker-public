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
    """Stream a job's progress to the client over Server-Sent Events.

    :param job_id: The job to stream.
    :param job_queue: The injected job queue service.
    :returns: An :class:`EventSourceResponse` emitting JSON job-status events until the
        job reaches a terminal state.
    """
    async def event_generator():
        async for job_status in job_queue.stream_progress(job_id):
            yield {"data": job_status.model_dump_json()}

    return EventSourceResponse(event_generator())
