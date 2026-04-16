from app.tasks.celery_app import celery_app


@celery_app.task
def classifier_training_task(
    topics: list[dict], doc_ids: list[str]
) -> dict:
    """Train FastText classifier.
    Depends on: ClassifierWrapper, SearchService, ClassifierLibraryService."""
    raise NotImplementedError
