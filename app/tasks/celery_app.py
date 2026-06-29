"""Celery application instance for the background worker.

Builds the shared ``celery_app``, loads its configuration from ``app.config`` under the
``CELERY`` namespace, and autodiscovers the task modules when ``CELERY_AUTODISCOVER`` is
set (only the worker process needs to import the heavy NLP tasks).
"""

import os
import time

from celery import Celery
from celery.signals import task_prerun, task_postrun

from app.infrastructure.timing import log_timing

celery_app = Celery("acteu")
celery_app.config_from_object("app.config", namespace="CELERY")

if os.getenv("CELERY_AUTODISCOVER") == "1":
	celery_app.autodiscover_tasks(["app.tasks"])


# --- Performance timing ( pipeline jobs) -----------------------------
# Measure pure worker execution time for every task uniformly, without touching
# task code. ``start_ts`` (wall clock) is logged so the parser can pair it with the
# matching ``event=dispatch`` record (from JobQueueService) and derive queue-wait.
_task_starts: dict[str, tuple[float, float]] = {}


@task_prerun.connect
def _timing_task_prerun(task_id: str = "", task=None, **_: object) -> None:
	_task_starts[task_id] = (time.perf_counter(), time.time())


@task_postrun.connect
def _timing_task_postrun(task_id: str = "", task=None, state: str = "", **_: object) -> None:
	started = _task_starts.pop(task_id, None)
	if started is None:
		return
	start_perf, start_wall = started
	duration_ms = (time.perf_counter() - start_perf) * 1000
	log_timing(
		getattr(task, "name", "unknown"),
		event="task",
		job_id=task_id,
		state=state,
		start_ts=start_wall,
		dur_ms=duration_ms,
	)
