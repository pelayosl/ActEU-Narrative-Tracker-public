from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.search import SearchQuery
from app.schemas.topic import Topic


class ClassificationService:
    """Orchestration only — dispatches tasks, no repository access."""

    def __init__(self, job_queue: JobQueueService) -> None:
        self._job_queue = job_queue

    def submit_training(self, topics: list[Topic], doc_ids: list[str], project_id: str) -> str:
        raise NotImplementedError

    def submit_labelling(self, project_id: str, classifier_id: str, query: SearchQuery) -> str:
        raise NotImplementedError
