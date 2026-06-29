"""Performance-timing log helper (infrastructure, no business logic).

Emits one structured single-line record per measured operation to a dedicated log
file (``settings.TIMING_LOG_PATH``), kept separate from the application logs so it can
be parsed without noise (see ``scripts/parse_timings.py``).

Two producers write here:

* the API-Gateway request middleware (``app.main``) — one ``event=request`` line per
  user-facing HTTP call (search, visualisation, synchronous Phase 1 labelling, ...);
* the Celery signal handlers (``app.tasks.celery_app``) — one ``event=dispatch`` line
  when a job is enqueued and one ``event=task`` line when the worker finishes it.

The API and the worker run in separate processes (separate containers), so they write
to separate files; the parser accepts a glob and pairs ``dispatch``/``task`` records by
``job_id`` to derive queue-wait latency.

Each record is ``<asctime> op=<name> key=value ...``. Always present: ``ts`` (epoch
seconds, for cross-process pairing). Failure to log never propagates to the caller.
"""

import logging
import time

from app.config import settings

_timing_logger = logging.getLogger("acteu.timing")


def _configure() -> logging.Logger:
    """Attach a single file handler to the timing logger (idempotent)."""
    if _timing_logger.handlers:
        return _timing_logger
    handler = logging.FileHandler(settings.TIMING_LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _timing_logger.addHandler(handler)
    _timing_logger.setLevel(logging.INFO)
    # Keep timing records out of the application/uvicorn log stream.
    _timing_logger.propagate = False
    return _timing_logger


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    text = str(value)
    # Keep every record a clean set of key=value tokens: no spaces in values.
    return text.replace(" ", "_")


def log_timing(op: str, **fields: object) -> None:
    """Append one timing record.

    :param op: The operation name (e.g. a task name or ``"POST /search"``).
    :param fields: Arbitrary ``key=value`` measurements (``dur_ms``, ``status``, ...).
        ``ts`` (epoch seconds) is added automatically when not supplied.
    """
    try:
        fields.setdefault("ts", time.time())
        parts = " ".join(f"{k}={_fmt(v)}" for k, v in fields.items())
        _configure().info("op=%s %s", _fmt(op), parts)
    except Exception:  # noqa: BLE001 — measurement must never break the request/task
        pass
