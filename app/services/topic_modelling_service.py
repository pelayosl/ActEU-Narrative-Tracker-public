from app.infrastructure.job_queue_service import JobQueueService


class TopicModellingService:
    """Orchestration for the topic-modelling pipeline steps.

    Dispatches the BERTopic generation and LLM reconciliation tasks to Celery via the
    job queue, returning a job id the caller can stream for progress.
    """

    def __init__(self, job_queue: JobQueueService) -> None:
        """Store the job queue used to dispatch tasks.

        :param job_queue: Infrastructure service that dispatches Celery tasks.
        """
        self._job_queue = job_queue

    def submit_generation(self, project_id: str, doc_ids: list[str]) -> str:
        """Dispatch a BERTopic topic-generation job.

        :param project_id: The project the generated pipeline state belongs to.
        :param doc_ids: The documents to run topic modelling over.
        :returns: The dispatched job's id.
        """
        return self._job_queue.dispatch(
            "app.tasks.topic_generation_task.topic_generation_task",
            {"project_id": project_id, "doc_ids": doc_ids},
        )

    def submit_reconciliation(
        self, project_id: str, topics: list[dict], passthrough_topics: list[dict] | None = None
    ) -> str:
        """Dispatch an LLM topic-reconciliation job.

        :param project_id: The project whose pending pipeline will be updated.
        :param topics: The topics to reconcile.
        :param passthrough_topics: Topics kept unchanged and appended to the final
            list (defaults to empty when only a selection is reconciled).
        :returns: The dispatched job's id.
        """
        return self._job_queue.dispatch(
            "app.tasks.reconciliation_task.reconciliation_task",
            {
                "project_id": project_id,
                "topics": topics,
                "passthrough_topics": passthrough_topics or [],
            },
        )
