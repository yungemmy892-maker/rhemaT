import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("verseid")
# Reads every CELERY_* setting from config/settings.py (namespace="CELERY"
# strips that prefix — e.g. CELERY_BROKER_URL becomes broker_url).
app.config_from_object("django.conf:settings", namespace="CELERY")
# Picks up tasks.py from every app in INSTALLED_APPS automatically —
# billing/tasks.py and notifications/tasks.py, plus anything added later.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Matches billing/scheduler.py's old INTERVAL_SECONDS (6 hours).
    "charge-subscription-renewals": {
        "task": "billing.tasks.charge_renewals",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Downgrades cancelled subscriptions once their paid-up period has
    # actually ended (see billing/management/commands/expire_subscriptions.py).
    # Runs hourly so nobody keeps Pro access much longer than promised, but
    # doesn't need charge_renewals' 6-hour cadence since there's no
    # external charge to coordinate here.
    "expire-cancelled-subscriptions": {
        "task": "billing.tasks.expire_subscriptions",
        "schedule": crontab(minute=0),
    },
    # Matches notifications/scheduler.py's old INTERVAL_SECONDS (15 min).
    "send-daily-verse": {
        "task": "notifications.tasks.send_daily_verse",
        "schedule": crontab(minute="*/15"),
    },
}
