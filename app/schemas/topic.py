from __future__ import annotations

from pydantic import BaseModel


# Reserved label for the BERTopic outlier cluster (-1). Used internally to train
# the classifier to recognise documents that match no real topic, so it can avoid
# forcing a label onto them. Never shown to the user, never added to a generated
# topic, and never persisted to a document proxy.
OTHER_TOPIC_ID = "__other__"


class Topic(BaseModel):
    topic_id: str
    name: str
    description: str
    origin_topic_ids: list[str] = []
    # The core ACTEU slug ("immigration"/"climate_change"/"gender_issues") for the 3
    # core topics; None for every subtopic (db-native and project-generated alike).
    core_topic: str | None = None


class GenerateTopicsRequest(BaseModel):
    project_id: str
    doc_ids: list[str]


class ReconciliationRequest(BaseModel):
    project_id: str
    topics: list[Topic]


class GenerateTopicsResponse(BaseModel):
    topics: list[Topic]


class ReconciliationResponse(BaseModel):
    topics: list[Topic]
