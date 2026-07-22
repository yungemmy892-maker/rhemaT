# Makes sure the Celery app (config/celery.py) is always imported when
# Django starts, so @shared_task decorators anywhere in the project pick
# up this app's config without each task module importing celery.py itself.
from .celery import app as celery_app

__all__ = ("celery_app",)
