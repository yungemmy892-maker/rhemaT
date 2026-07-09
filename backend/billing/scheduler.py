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