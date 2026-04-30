from __future__ import annotations

from pydantic import BaseModel


class Topic(BaseModel):
    topic_id: str
    name: str
    description: str
    core_topic: str
