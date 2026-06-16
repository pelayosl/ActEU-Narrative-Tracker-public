from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.search import SearchQuery
from app.schemas.topic import Topic
from app.services.classification_service import ClassificationService

TRAINING_TASK = "app.tasks.classifier_training_task.classifier_training_task"
LABELLING_TASK = "app.tasks.labelling_task.labelling_task"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def job_queue() -> Mock:
    # dispatch() is synchronous and returns a job_id string.
    queue = Mock(spec=JobQueueService)
    queue.dispatch.return_value = "job-123"
    return queue


@pytest.fixture
def service(job_queue) -> ClassificationService:
    return ClassificationService(job_queue)


def make_topic(**overrides) -> Topic:
    base = {"topic_id": "t1", "name": "Immigration policy", "description": "desc"}
    base.update(overrides)
    return Topic(**base)


# ---------------------------------------------------------------------------
# submit_training()
# ---------------------------------------------------------------------------

class TestSubmitTraining:
    async def test_dispatches_training_task(self, service, job_queue):
        service.submit_training([make_topic()], "proj-1", "My classifier")

        job_queue.dispatch.assert_called_once()
        task_name = job_queue.dispatch.call_args.args[0]
        assert task_name == TRAINING_TASK

    async def test_returns_dispatched_job_id(self, service, job_queue):
        job_queue.dispatch.return_value = "abc-789"

        job_id = service.submit_training([make_topic()], "proj-1", "name")

        assert job_id == "abc-789"

    async def test_payload_carries_project_and_name(self, service, job_queue):
        service.submit_training([make_topic()], "proj-1", "My classifier")

        kwargs = job_queue.dispatch.call_args.args[1]
        assert kwargs["project_id"] == "proj-1"
        assert kwargs["name"] == "My classifier"

    async def test_topics_serialised_to_plain_dicts(self, service, job_queue):
        """Topics must cross the Celery boundary as JSON-safe dicts, not Topic objects."""
        topics = [make_topic(topic_id="t1"), make_topic(topic_id="t2")]

        service.submit_training(topics, "proj-1", "name")

        kwargs = job_queue.dispatch.call_args.args[1]
        sent = kwargs["topics"]
        assert all(isinstance(t, dict) for t in sent)
        assert [t["topic_id"] for t in sent] == ["t1", "t2"]

    async def test_topic_fields_preserved_in_payload(self, service, job_queue):
        topic = make_topic(
            topic_id="t9",
            name="Climate",
            description="climate desc",
            origin_topic_ids=["a", "b"],
            core_topic="climate_change",
        )

        service.submit_training([topic], "proj-1", "name")

        sent = job_queue.dispatch.call_args.args[1]["topics"][0]
        assert sent["name"] == "Climate"
        assert sent["description"] == "climate desc"
        assert sent["origin_topic_ids"] == ["a", "b"]
        assert sent["core_topic"] == "climate_change"

    async def test_empty_topic_list_is_allowed(self, service, job_queue):
        service.submit_training([], "proj-1", "name")

        assert job_queue.dispatch.call_args.args[1]["topics"] == []


# ---------------------------------------------------------------------------
# submit_labelling()
# ---------------------------------------------------------------------------

class TestSubmitLabelling:
    async def test_dispatches_labelling_task(self, service, job_queue):
        service.submit_labelling("proj-1", "clf-1", SearchQuery())

        task_name = job_queue.dispatch.call_args.args[0]
        assert task_name == LABELLING_TASK

    async def test_returns_dispatched_job_id(self, service, job_queue):
        job_queue.dispatch.return_value = "label-job-1"

        job_id = service.submit_labelling("proj-1", "clf-1", SearchQuery())

        assert job_id == "label-job-1"

    async def test_payload_carries_project_and_classifier(self, service, job_queue):
        service.submit_labelling("proj-1", "clf-1", SearchQuery())

        kwargs = job_queue.dispatch.call_args.args[1]
        assert kwargs["project_id"] == "proj-1"
        assert kwargs["classifier_id"] == "clf-1"

    async def test_query_serialised_to_dict(self, service, job_queue):
        query = SearchQuery(keywords=["climate"], confidence_threshold=0.7)

        service.submit_labelling("proj-1", "clf-1", query)

        sent = job_queue.dispatch.call_args.args[1]["query"]
        assert isinstance(sent, dict)
        assert sent["keywords"] == ["climate"]
        assert sent["confidence_threshold"] == 0.7

    async def test_query_datetimes_are_json_serialisable(self, service, job_queue):
        """mode='json' must turn datetimes into strings so Celery/JSON can carry them."""
        query = SearchQuery(
            date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        service.submit_labelling("proj-1", "clf-1", query)

        sent = job_queue.dispatch.call_args.args[1]["query"]
        assert isinstance(sent["date_from"], str)
        assert isinstance(sent["date_to"], str)
