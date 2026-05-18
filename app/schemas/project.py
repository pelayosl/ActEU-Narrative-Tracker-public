from datetime import datetime

from pydantic import BaseModel

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.topic import Topic


class PendingPipeline(BaseModel):
    generation_job_id: str
    generated_topics: list[Topic] = []
    reconciled_topics: list[Topic] = []
    topic_mapping: dict[str, list[str]] = {}
    created_at: datetime


class Project(BaseModel):
    project_id: str
    owner_id: str
    name: str
    created_at: datetime
    classifiers: list[ClassifierMetadata] = []
    document_proxies: list[DocumentProxy] = []
    pending_pipeline: PendingPipeline | None = None
