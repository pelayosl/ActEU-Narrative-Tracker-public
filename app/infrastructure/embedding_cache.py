import numpy as np


class EmbeddingCache:
    """Cache embeddings on disk keyed by hash of doc_ids."""

    def get(self, doc_ids: list[str]) -> np.ndarray | None:
        raise NotImplementedError

    def store(self, doc_ids: list[str], embeddings: np.ndarray) -> None:
        raise NotImplementedError
