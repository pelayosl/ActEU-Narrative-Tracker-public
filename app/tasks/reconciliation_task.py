from app.tasks.celery_app import celery_app


@celery_app.task
def reconciliation_task(topics: list[dict]) -> list[dict]:
    """Reconcile topics via LLMClient.
    No repository dependencies — results returned via SSE."""
    raise NotImplementedError
