"""Task module imports for Celery autodiscovery.

Celery's autodiscover_tasks looks for a `tasks` module by default. Importing the
task modules here ensures they are registered when `app.tasks` is imported.
"""

import os

if os.getenv("CELERY_AUTODISCOVER") == "1":
	from app.tasks import classifier_training_task
	from app.tasks import labelling_task
	from app.tasks import reconciliation_task
	from app.tasks import topic_generation_task 

	__all__ = [
		"classifier_training_task",
		"labelling_task",
		"reconciliation_task",
		"topic_generation_task",
	]
else:
	__all__ = []
