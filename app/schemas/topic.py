from __future__ import annotations

from pydantic import BaseModel


class Topic(BaseModel):
    topic_id: str
    name: str
    description: str
    origin_topic_ids: list[str] = []


class GenerateTopicsRequest(BaseModel):
    doc_ids: list[str]


class GenerateTopicsResponse(BaseModel):
    topics: list[Topic]


class ReconciliationResponse(BaseModel):
    topics: list[Topic]
