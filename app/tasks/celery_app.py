from celery import Celery

celery_app = Celery("acteu")
celery_app.config_from_object("app.config", namespace="CELERY")
