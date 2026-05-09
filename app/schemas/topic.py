from __future__ import annotations

from pydantic import BaseModel


class Topic(BaseModel):
    topic_id: str
    name: str
    description: str


class GenerateTopicsRequest(BaseModel):
    doc_ids: list[str]


class GenerateTopicsResponse(BaseModel):
    topics: list[Topic]
