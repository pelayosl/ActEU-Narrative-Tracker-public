from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_current_user, get_job_queue
from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.auth import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
    _: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    '''
    SSE endpoint the frontend connects to after receiving a job_id
    '''
    async def event_generator():
        async for job_status in job_queue.stream_progress(job_id):
            yield {"data": job_status.model_dump_json()}

    return EventSourceResponse(event_generator())
