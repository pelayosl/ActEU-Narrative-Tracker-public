from app.schemas.topic import Topic


class LLMClient:
    """Gemini API wrapper via LiteLLM. Lives in services (not infrastructure)
    because it encapsulates prompt engineering, response parsing and retry logic."""

    async def reconcile(self, topics: list[Topic]) -> list[Topic]:
        raise NotImplementedError
