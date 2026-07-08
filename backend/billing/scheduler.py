"""
Runs `manage.py charge_renewals` automatically in a background thread, so
Pro subscriptions actually auto-renew without needing an external cron job
configured on whatever platform this gets deployed to. Started from
BillingConfig.ready() (see apps.py) — same pattern as
notifications/scheduler.py for the daily verse notification.

Runs every 6 hours rather than every 15 minutes (unlike the daily-verse
scheduler): renewal is date-based, not time-of-day-window-based, and
Subscription.last_renewal_attempt_date already guards against charging the
same subscription twice in one day even if this fires more than once.

Same multi-worker caveat as the notifications scheduler: in a deployment
with several gunicorn workers, each starts its own copy of this thread. The
last_renewal_attempt_date guard makes a double-charge on the same day
extremely unlikely (not impossible, if two workers both read "not yet
attempted today" within the same race window) rather than a real problem,
but for a production deployment with several workers, prefer a real
external scheduler hitting `charge_renewals` and set
DISABLE_INPROCESS_SCHEDULER=true (shared with the notifications scheduler)
to turn both off.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 6 * 60 * 60

_started = False
_lock = threading.Lock()


def start_scheduler() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True

    thread = threading.Thread(target=_loop, name="subscription-renewal-scheduler", daemon=True)
    thread.start()
    logger.info("Subscription renewal scheduler started (every %d hours).", INTERVAL_SECONDS // 3600)


def _loop() -> None:
    from django.core.management import call_command

    while True:
        try:
            call_command("charge_renewals")
        except Exception:
            logger.exception("charge_renewals run failed")
        time.sleep(INTERVAL_SECONDS)