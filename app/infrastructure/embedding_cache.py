import hashlib
import logging
import sqlite3
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# SQLite caps the number of bound parameters per statement; keep IN-clauses well
# under the historical 999 limit so a single generation run can look up thousands
# of documents in batches.
_QUERY_BATCH = 900


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """Disk cache for document embeddings, keyed by a SHA-256 of the document text.

    Backed by a single SQLite file per embedding model (``<model>.db``). Keying by
    text hash — not doc_id — means the cache survives a database reload (which mints
    new ObjectIds) and naturally de-duplicates identical texts.

    The cache is non-authoritative: it stores only derived data and may be deleted
    at any time at the cost of a one-time recompute. Every operation is best-effort
    — any I/O failure degrades to a miss (or a no-op write) and is logged, never
    raised, so a cache problem can never fail the pipeline.
    """

    def __init__(self, cache_dir: str, model_name: str) -> None:
        slug = model_name.replace("/", "_")
        self._conn: sqlite3.Connection | None = None
        try:
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            db_path = str(Path(cache_dir) / f"{slug}.db")
            # timeout + busy_timeout let concurrent worker processes (Celery prefork)
            # serialise writes instead of failing with "database is locked".
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS embeddings (hash TEXT PRIMARY KEY, vec BLOB NOT NULL)"
            )
            self._conn = conn
        except Exception as e:
            logger.warning("EmbeddingCache disabled (init failed: %s)", e)

    def get_many(self, texts: list[str]) -> tuple[dict[str, np.ndarray], list[str]]:
        """Look up embeddings for ``texts``. Returns ``(cached, missing)`` where
        ``cached`` maps text → embedding for hits and ``missing`` is the
        de-duplicated list of texts that must still be computed."""
        # De-duplicate by hash while preserving first-seen order.
        unique: list[tuple[str, str]] = []
        seen: set[str] = set()
        for text in texts:
            h = _hash(text)
            if h not in seen:
                seen.add(h)
                unique.append((text, h))

        rows: dict[str, bytes] = {}
        if self._conn is not None:
            try:
                for start in range(0, len(unique), _QUERY_BATCH):
                    chunk = unique[start:start + _QUERY_BATCH]
                    placeholders = ",".join("?" * len(chunk))
                    cursor = self._conn.execute(
                        f"SELECT hash, vec FROM embeddings WHERE hash IN ({placeholders})",
                        [h for _, h in chunk],
                    )
                    for h, blob in cursor.fetchall():
                        rows[h] = blob
            except Exception as e:
                logger.warning("EmbeddingCache read failed (%s), treating as miss", e)
                rows = {}

        cached: dict[str, np.ndarray] = {}
        missing: list[str] = []
        for text, h in unique:
            blob = rows.get(h)
            if blob is None:
                missing.append(text)
            else:
                cached[text] = np.frombuffer(blob, dtype=np.float32).copy()
        return cached, missing

    def store_many(self, texts: list[str], embeddings: np.ndarray) -> None:
        """Persist ``embeddings`` (row-aligned with ``texts``). Best-effort: a
        failure is logged and swallowed."""
        if self._conn is None:
            return
        try:
            seen: set[str] = set()
            records: list[tuple[str, bytes]] = []
            for text, vec in zip(texts, embeddings):
                h = _hash(text)
                if h in seen:
                    continue
                seen.add(h)
                records.append((h, np.asarray(vec, dtype=np.float32).tobytes()))
            if records:
                with self._conn:
                    self._conn.executemany(
                        "INSERT OR REPLACE INTO embeddings (hash, vec) VALUES (?, ?)",
                        records,
                    )
        except Exception as e:
            logger.warning("EmbeddingCache write failed (%s), skipping", e)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
