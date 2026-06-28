import asyncio

from app.tasks.task_context import project_service_context
from app.schemas.topic import ReconciliationResponse, Topic
from app.services.llm_client import LLMClient
from app.tasks.celery_app import celery_app


@celery_app.task
def reconciliation_task(
    project_id: str, topics: list[dict], passthrough_topics: list[dict] | None = None
) -> dict:
    """Celery entry point for topic reconciliation.

    Reconciles topics via ``LLMClient`` and persists them into the project's pending
    pipeline.

    :param project_id: The project whose pending pipeline is updated.
    :param topics: The topics to reconcile, as plain dicts.
    :param passthrough_topics: Topics kept unchanged and appended to the final list.
    :returns: A serialised :class:`ReconciliationResponse`.
    """
    return asyncio.run(_run(project_id, topics, passthrough_topics or []))


async def _run(
    project_id: str, topics: list[dict], passthrough_topics: list[dict] | None = None
) -> dict:
    """Execute the async reconciliation for one job.

    Reconciles the topics, and on success persists ``reconciled + passthrough_topics``
    into the pending pipeline. When the LLM is unavailable it persists nothing and
    returns an empty topic list with ``llm_available=False``.

    :param project_id: The project whose pending pipeline is updated.
    :param topics: The topics to reconcile, as plain dicts.
    :param passthrough_topics: Topics kept unchanged and appended to the final list.
    :returns: A serialised :class:`ReconciliationResponse`.
    """
    passthrough_topics = passthrough_topics or []
    parsed = [Topic(**t) for t in topics]
    # Instantiated directly (not via task_context): LLMClient is stateless and
    # opens/closes its own HTTP connection per call.
    reconciled, llm_available = LLMClient().reconcile(parsed)

    # When the LLM is unavailable, do NOT persist the fallback.
    if not llm_available:
        return ReconciliationResponse(topics=[], llm_available=False).model_dump()

    # Unselected topics are excluded from reconciliation but kept in the final list.
    final_topics = reconciled + [Topic(**t) for t in passthrough_topics]

    async with project_service_context() as project_service:
        await project_service.update_reconciled_topics(project_id, final_topics)

    return ReconciliationResponse(topics=final_topics, llm_available=True).model_dump()
