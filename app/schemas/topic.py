from __future__ import annotations

from pydantic import BaseModel


class Topic(BaseModel):
    topic_id: str
    name: str
    description: str
    doc_ids: list[str] = []
    origin_topics: list[Topic] | None = None
