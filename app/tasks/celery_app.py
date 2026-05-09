import os

from celery import Celery

celery_app = Celery("acteu")
celery_app.config_from_object("app.config", namespace="CELERY")

if os.getenv("CELERY_AUTODISCOVER") == "1":
	celery_app.autodiscover_tasks(["app.tasks"])
