import asyncio

from app.infrastructure.task_db import project_service_context
from app.schemas.topic import ReconciliationResponse, Topic
from app.services.llm_client import LLMClient
from app.tasks.celery_app import celery_app


@celery_app.task
def reconciliation_task(project_id: str, topics: list[dict]) -> dict:
    """Reconcile topics via LLMClient and persist them in the project's pending pipeline."""
    return asyncio.run(_run(project_id, topics))


async def _run(project_id: str, topics: list[dict]) -> dict:
    parsed = [Topic(**t) for t in topics]
    reconciled = LLMClient().reconcile(parsed)

    async with project_service_context() as project_service:
        await project_service.update_reconciled_topics(project_id, reconciled)

    return ReconciliationResponse(topics=reconciled).model_dump()
