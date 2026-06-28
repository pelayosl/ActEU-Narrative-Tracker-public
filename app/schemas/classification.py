from datetime import datetime

from pydantic import BaseModel

from app.schemas.search import SearchQuery
from app.schemas.topic import Topic


class TrainClassifierRequest(BaseModel):
    """Request body for training a classifier on selected topics within a project."""

    topics: list[Topic]
    project_id: str
    name: str


class ClassifierMetadata(BaseModel):
    """A trained classifier embedded in a project, with its topics and model file path.

    Ownership is implicit through the parent project, so no ``owner_id`` is stored.
    """

    classifier_id: str
    name: str
    topics: list[Topic]
    file_path: str
    created_at: datetime


class ProxyLabel(BaseModel):
    """A single classifier-assigned label on a document proxy, with its confidence."""

    topic_id: str
    name: str
    description: str
    classifier_id: str
    confidence: float | None = None


class DocumentProxy(BaseModel):
    """A project's reference to a core document, carrying the labels assigned to it."""

    doc_id: str
    labels: list[ProxyLabel] = []


class LabellingResult(BaseModel):
    """Summary of a labelling run: how many documents were labelled, broken down by topic."""

    project_id: str
    total_labelled: int
    topic_summary: dict[str, int]


class LabelRequest(BaseModel):
    """Request body for Phase 2 labelling of a new query within a project."""

    project_id: str
    classifier_id: str
    query: SearchQuery


class InitialLabelRequest(BaseModel):
    """Request body for Phase 1 labelling from the training-era topic mapping."""

    project_id: str
    classifier_id: str
