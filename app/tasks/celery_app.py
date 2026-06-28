"""Celery application instance for the background worker.

Builds the shared ``celery_app``, loads its configuration from ``app.config`` under the
``CELERY`` namespace, and autodiscovers the task modules when ``CELERY_AUTODISCOVER`` is
set (only the worker process needs to import the heavy NLP tasks).
"""

import os

from celery import Celery

celery_app = Celery("acteu")
celery_app.config_from_object("app.config", namespace="CELERY")

if os.getenv("CELERY_AUTODISCOVER") == "1":
	celery_app.autodiscover_tasks(["app.tasks"])
