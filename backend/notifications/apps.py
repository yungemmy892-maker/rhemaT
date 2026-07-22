from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "notifications"

    # NOTE: this used to start an in-process thread here that called
    # send_daily_verse on a timer (see git history / the old
    # notifications/scheduler.py). It ran once per gunicorn WORKER process,
    # so more than one worker meant multiple threads sending the daily
    # verse on the same schedule. Replaced by a Celery Beat periodic task —
    # see notifications/tasks.py and config/celery.py.
