from pydantic import BaseModel


class JobStatus(BaseModel):
    """Snapshot of a background job's state, streamed to the frontend over SSE."""

    job_id: str
    status: str
    progress: int
    result: dict = {}
