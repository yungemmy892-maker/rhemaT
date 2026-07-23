import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from notifications.models import Notification
from users.models import User

from billing.models import Subscription

logger = logging.getLogger(__name__)


def _now() -> datetime.datetime:
    """
    UTC "now" via Django's non-deprecated timezone-aware clock, with
    tzinfo stripped before use — matches the naive-UTC convention every
    other DateTimeField in this codebase relies on (see the identical
    helper in billing/views.py and charge_renewals.py for the full
    rationale).
    """
    return dj_timezone.now().replace(tzinfo=None)


class Command(BaseCommand):

    help = (
        "Downgrades users whose cancelled subscription has passed its "
        "current_period_end. Run hourly via Celery Beat."
    )

    def handle(self, *args, **options):
        now = _now()

        due = Subscription.objects(
            status="cancelled", current_period_end__lt=now
        )
        due_subs = list(due)
        self.stdout.write(f"{len(due_subs)} cancelled subscription(s) past their period end.")

        expired = skipped = 0

        for sub in due_subs:
            # Atomically claim this subscription for expiry — mirrors the
            # same race-safety pattern charge_renewals.py uses. Only a
            # worker that actually flips status "cancelled" -> "expired"
            # proceeds to downgrade the user; a losing worker (two Celery
            # Beat/worker processes overlapping, or a manual + scheduled
            # run colliding) just matches zero documents and moves on,
            # instead of both racing to write the same user.
            claimed = Subscription.objects(
                id=sub.id, status="cancelled"
            ).update(set__status="expired", set__updated_at=now)
            if not claimed:
                skipped += 1
                continue

            user = User.objects(id=sub.user_id).first()
            if user is None:
                skipped += 1
                continue

            user.plan = "Free"
            user.plan_expires_at = None
            user.save()
            expired += 1

        self.stdout.write(
            self.style.SUCCESS(f"Expired: {expired}, Skipped: {skipped}")
        )
