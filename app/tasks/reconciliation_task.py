import asyncio

from app.tasks.task_context import project_service_context
from app.schemas.topic import ReconciliationResponse, Topic
from app.services.llm_client import LLMClient
from app.tasks.celery_app import celery_app


@celery_app.task
def reconciliation_task(project_id: str, topics: list[dict]) -> dict:
    """Reconcile topics via LLMClient and persist them in the project's pending pipeline."""
    return asyncio.run(_run(project_id, topics))


async def _run(project_id: str, topics: list[dict]) -> dict:
    parsed = [Topic(**t) for t in topics]
    # Instantiated directly (not via task_context): LLMClient is stateless and
    # opens/closes its own HTTP connection per call.
    reconciled, llm_available = LLMClient().reconcile(parsed)

    # When the LLM is unavailable, do NOT persist the fallback.
    if not llm_available:
        return ReconciliationResponse(topics=[], llm_available=False).model_dump()

    async with project_service_context() as project_service:
        await project_service.update_reconciled_topics(project_id, reconciled)

    return ReconciliationResponse(topics=reconciled, llm_available=True).model_dump()
