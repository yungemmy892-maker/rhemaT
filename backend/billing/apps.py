from django.apps import AppConfig


class BillingConfig(AppConfig):
    name = "billing"

    # NOTE: this used to start an in-process thread here that called
    # charge_renewals on a timer (see git history / the old
    # billing/scheduler.py). It ran once per gunicorn WORKER process, so
    # more than one worker meant multiple threads charging renewals on the
    # same schedule. Replaced by a Celery Beat periodic task — see
    # billing/tasks.py and config/celery.py.
