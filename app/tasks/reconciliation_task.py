from app.schemas.topic import ReconciliationResponse, Topic
from app.services.llm_client import LLMClient
from app.tasks.celery_app import celery_app


@celery_app.task
def reconciliation_task(topics: list[dict]) -> dict:
    """Reconcile topics via LLMClient.
    No repository dependencies — results returned via SSE."""
    parsed = [Topic(**t) for t in topics]
    reconciled = LLMClient().reconcile(parsed)
    return ReconciliationResponse(topics=reconciled).model_dump()
