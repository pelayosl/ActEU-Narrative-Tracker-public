from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.search import SearchQuery
from app.schemas.topic import Topic


class ClassificationService:
    """Orchestration only, dispatches classification tasks with no repository access.

    Hands classifier training and Phase 2 labelling off to Celery via the job queue,
    returning a job id the caller can stream for progress.
    """

    def __init__(self, job_queue: JobQueueService) -> None:
        """Store the job queue used to dispatch tasks.

        :param job_queue: Infrastructure service that dispatches Celery tasks.
        """
        self._job_queue = job_queue

    def submit_training(
        self,
        topics: list[Topic],
        project_id: str,
        name: str,
    ) -> str:
        """Dispatch a classifier-training job.

        :param topics: The topics to train the classifier on.
        :param project_id: The project the classifier will belong to.
        :param name: The name to give the trained classifier.
        :returns: The dispatched job's id.
        """
        return self._job_queue.dispatch(
            "app.tasks.classifier_training_task.classifier_training_task",
            {
                "topics": [t.model_dump() for t in topics],
                "project_id": project_id,
                "name": name,
            },
        )

    def submit_labelling(
        self, project_id: str, classifier_id: str, query: SearchQuery
    ) -> str:
        """Dispatch a Phase 2 labelling job for a new query within a project.

        :param project_id: The project whose proxies will receive the labels.
        :param classifier_id: The classifier used to predict labels.
        :param query: The search query selecting the documents to label.
        :returns: The dispatched job's id.
        """
        return self._job_queue.dispatch(
            "app.tasks.labelling_task.labelling_task",
            {
                "project_id": project_id,
                "classifier_id": classifier_id,
                "query": query.model_dump(mode="json"),
            },
        )
