"""Unit tests for EmbeddingCache (pure SQLite I/O, no Mongo/NLP — runs in CI)."""
import numpy as np

from app.infrastructure.embedding_cache import EmbeddingCache


def test_store_and_get_roundtrip(tmp_path):
    cache = EmbeddingCache(str(tmp_path), "test/model")
    texts = ["hello world", "second document"]
    embs = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)

    cache.store_many(texts, embs)
    cached, missing = cache.get_many(texts)

    assert missing == []
    assert np.allclose(cached["hello world"], embs[0])
    assert np.allclose(cached["second document"], embs[1])
    cache.close()


def test_partial_miss_reports_uncached_texts(tmp_path):
    cache = EmbeddingCache(str(tmp_path), "m")
    cache.store_many(["a"], np.array([[1.0, 2.0]], dtype=np.float32))

    cached, missing = cache.get_many(["a", "b"])

    assert list(cached.keys()) == ["a"]
    assert missing == ["b"]
    cache.close()


def test_persists_across_instances(tmp_path):
    """The whole point: a fresh process/instance reads the previous run's vectors."""
    c1 = EmbeddingCache(str(tmp_path), "m")
    c1.store_many(["x"], np.array([[9.0, 8.0]], dtype=np.float32))
    c1.close()

    c2 = EmbeddingCache(str(tmp_path), "m")
    cached, missing = c2.get_many(["x"])

    assert missing == []
    assert np.allclose(cached["x"], [9.0, 8.0])
    c2.close()


def test_missing_is_deduplicated(tmp_path):
    cache = EmbeddingCache(str(tmp_path), "m")

    cached, missing = cache.get_many(["dup", "dup"])

    assert cached == {}
    assert missing == ["dup"]
    cache.close()


def test_model_namespacing_isolates_caches(tmp_path):
    """Different models must not read each other's vectors."""
    a = EmbeddingCache(str(tmp_path), "model-a")
    a.store_many(["shared text"], np.array([[1.0]], dtype=np.float32))
    a.close()

    b = EmbeddingCache(str(tmp_path), "model-b")
    cached, missing = b.get_many(["shared text"])

    assert missing == ["shared text"]
    b.close()


def test_disabled_cache_degrades_to_all_miss(tmp_path):
    """An unusable cache dir must not raise — it reports every text as a miss."""
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory")  # mkdir over a file fails → disabled mode

    cache = EmbeddingCache(str(blocker), "m")
    cache.store_many(["a"], np.array([[1.0]], dtype=np.float32))  # no-op, no raise
    cached, missing = cache.get_many(["a"])

    assert cached == {}
    assert missing == ["a"]
    cache.close()
