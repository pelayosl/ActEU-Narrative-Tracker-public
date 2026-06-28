from datetime import datetime

from pydantic import BaseModel

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.topic import Topic


class PendingPipeline(BaseModel):
    """In-progress pipeline state embedded in a project, allowing resumption.

    Holds the generated and reconciled topics plus the ``topic_mapping`` (topic_id to
    doc_ids, including the reserved ``OTHER_TOPIC_ID`` outlier entry) until Phase 1
    labelling clears it. ``classifier_id`` is stamped on successful training and lets
    Phase 1 detect a pipeline that a newer run has overwritten.
    """

    generation_job_id: str
    generated_topics: list[Topic] = []
    reconciled_topics: list[Topic] = []
    topic_mapping: dict[str, list[str]] = {}
    created_at: datetime
    classifier_id: str | None = None  # stamped by ClassifierTrainingTask on success


class Project(BaseModel):
    """A user-owned project embedding its classifiers, document proxies and pipeline state.

    All pipeline work happens inside a project, the core documents collection is never
    mutated.
    """

    project_id: str
    owner_id: str
    name: str
    created_at: datetime
    classifiers: list[ClassifierMetadata] = []
    document_proxies: list[DocumentProxy] = []
    pending_pipeline: PendingPipeline | None = None
