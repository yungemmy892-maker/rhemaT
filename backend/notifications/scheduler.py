"""
Runs `manage.py send_daily_verse` automatically, in a background thread,
every 15 minutes — so daily verse notifications actually go out without
needing an external cron job configured on whatever platform this gets
deployed to. Started from NotificationsConfig.ready() (see apps.py).

Caveat: in a multi-worker deployment (gunicorn -w 4, etc.) each worker
process starts its own copy of this thread, so multiple workers race to
send the same batch every 15 minutes. send_daily_verse's own
last-sent-today guard makes this at-worst a rare double-send (if two
workers both read a user's last_daily_sent_date as "not today" in the same
few hundred milliseconds) rather than a real duplication problem, but for
a production deployment with several workers, prefer a real external
scheduler hitting `send_daily_verse` and set DISABLE_INPROCESS_SCHEDULER=true
to turn this off entirely.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 15 * 60

_started = False
_lock = threading.Lock()


def start_scheduler() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True

    thread = threading.Thread(target=_loop, name="daily-verse-scheduler", daemon=True)
    thread.start()
    logger.info("Daily verse scheduler started (every %d minutes).", INTERVAL_SECONDS // 60)


def _loop() -> None:
    from django.core.management import call_command

    while True:
        try:
            call_command("send_daily_verse")
        except Exception:
            logger.exception("send_daily_verse run failed")
        time.sleep(INTERVAL_SECONDS)
