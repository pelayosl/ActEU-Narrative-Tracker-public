from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.search import SearchQuery
from app.schemas.topic import Topic


class ClassificationService:
    """Orchestration only — dispatches tasks, no repository access."""

    def __init__(self, job_queue: JobQueueService) -> None:
        self._job_queue = job_queue

    def submit_training(
        self,
        topics: list[Topic],
        project_id: str,
        generation_job_id: str,
        name: str,
    ) -> str:
        return self._job_queue.dispatch(
            "app.tasks.classifier_training_task.classifier_training_task",
            {
                "topics": [t.model_dump() for t in topics],
                "project_id": project_id,
                "generation_job_id": generation_job_id,
                "name": name,
            },
        )

    def submit_labelling(self, project_id: str, classifier_id: str, query: SearchQuery) -> str:
        raise NotImplementedError
