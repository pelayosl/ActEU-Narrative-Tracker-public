from app.infrastructure.job_queue_service import JobQueueService


class TopicModellingService:
    def __init__(self, job_queue: JobQueueService) -> None:
        self._job_queue = job_queue

    def submit_generation(self, doc_ids: list[str]) -> str:
        raise NotImplementedError

    def submit_reconciliation(self, topics: list[dict]) -> str:
        raise NotImplementedError
