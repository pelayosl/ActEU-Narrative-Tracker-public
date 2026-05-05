from app.tasks.celery_app import celery_app


@celery_app.task
def labelling_task(classifier_id: str, query: dict) -> dict:
    """Label documents using a trained classifier.
    Depends on: ClassifierWrapper, SearchService, ProjectService."""
    raise NotImplementedError
