from app.tasks.celery_app import celery_app


@celery_app.task
def topic_generation_task(doc_ids: list[str]) -> list[dict]:
    """Run BERTopic on the given documents.
    No repository dependencies — results returned via SSE."""
    raise NotImplementedError
