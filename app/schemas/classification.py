from datetime import datetime

from pydantic import BaseModel

from app.schemas.topic import Topic


class ClassifierMetadata(BaseModel):
    classifier_id: str
    owner_id: str
    topics: list[Topic]
    file_path: str
    created_at: datetime


class LabellingResult(BaseModel):
    classifier_id: str
    total_labelled: int
    topic_summary: dict[str, int]
