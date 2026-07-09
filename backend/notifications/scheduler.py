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
