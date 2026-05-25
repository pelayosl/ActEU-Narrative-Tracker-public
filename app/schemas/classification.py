from datetime import datetime

from pydantic import BaseModel

from app.schemas.search import SearchQuery
from app.schemas.topic import Topic


class TrainClassifierRequest(BaseModel):
    topics: list[Topic]
    project_id: str
    name: str


class ClassifierMetadata(BaseModel):
    classifier_id: str
    name: str
    topics: list[Topic]
    file_path: str
    created_at: datetime


class ProxyLabel(BaseModel):
    topic_id: str
    name: str
    description: str
    classifier_id: str
    confidence: float | None = None


class DocumentProxy(BaseModel):
    doc_id: str
    labels: list[ProxyLabel] = []


class LabellingResult(BaseModel):
    project_id: str
    total_labelled: int
    topic_summary: dict[str, int]


class LabelRequest(BaseModel):
    project_id: str
    classifier_id: str
    query: SearchQuery


class InitialLabelRequest(BaseModel):
    project_id: str
    classifier_id: str
