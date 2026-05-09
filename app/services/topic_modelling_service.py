from app.infrastructure.job_queue_service import JobQueueService


class TopicModellingService:
    def __init__(self, job_queue: JobQueueService) -> None:
        self._job_queue = job_queue

    def submit_generation(self, doc_ids: list[str]) -> str:
        return self._job_queue.dispatch(
            "app.tasks.topic_generation_task.topic_generation_task",
            {"doc_ids": doc_ids},
        )

    def submit_reconciliation(self, topics: list[dict]) -> str:
        return self._job_queue.dispatch(
            "app.tasks.reconciliation_task.reconciliation_task",
            {"topics": topics},
        )
