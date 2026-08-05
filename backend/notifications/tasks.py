import logging

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

logger = logging.getLogger(__name__)

LOCK_KEY = "lock:send_daily_verse"
# Longer than the slowest run we've seen (~10 min) so a genuinely still-
# running job can't be double-started by an overlapping beat trigger, but
# short enough a crashed worker doesn't wedge the next real window.
LOCK_TIMEOUT = 60 * 20


@shared_task(name="notifications.tasks.send_daily_verse")
def send_daily_verse():
    # cache.add() is SETNX on the Redis/Upstash backend — only the first
    # caller within LOCK_TIMEOUT gets True; a duplicate beat fire just no-ops.
    if not cache.add(LOCK_KEY, "1", timeout=LOCK_TIMEOUT):
        logger.warning(
            "send_daily_verse already running — skipping this trigger."
        )
        return
    try:
        call_command("send_daily_verse")
    finally:
        cache.delete(LOCK_KEY)