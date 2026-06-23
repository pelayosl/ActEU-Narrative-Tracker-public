from app.infrastructure.job_queue_service import JobQueueService


class TopicModellingService:
    def __init__(self, job_queue: JobQueueService) -> None:
        self._job_queue = job_queue

    def submit_generation(self, project_id: str, doc_ids: list[str]) -> str:
        return self._job_queue.dispatch(
            "app.tasks.topic_generation_task.topic_generation_task",
            {"project_id": project_id, "doc_ids": doc_ids},
        )

    def submit_reconciliation(
        self, project_id: str, topics: list[dict], passthrough_topics: list[dict] | None = None
    ) -> str:
        return self._job_queue.dispatch(
            "app.tasks.reconciliation_task.reconciliation_task",
            {
                "project_id": project_id,
                "topics": topics,
                "passthrough_topics": passthrough_topics or [],
            },
        )
