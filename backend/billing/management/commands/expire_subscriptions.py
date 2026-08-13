import logging

from django.core.management.base import BaseCommand

from notifications.email import send_pro_expired_email
from notifications.models import Notification
from users.models import User

from billing.models import Subscription
from billing.services import now_utc

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        "Downgrades users whose cancelled subscription has passed its "
        "current_period_end. Run hourly via Celery Beat."
    )

    def handle(self, *args, **options):
        now = now_utc()

        due = Subscription.objects(status="cancelled", current_period_end__lt=now)
        due_subs = list(due)
        self.stdout.write(
            f"{len(due_subs)} cancelled subscription(s) past their period end."
        )

        expired = lost_race = orphaned = 0

        for sub in due_subs:
            # Atomically claim this subscription for expiry — mirrors the
            # same race-safety pattern charge_renewals.py uses. Only a
            # worker that actually flips status "cancelled" -> "expired"
            # proceeds to downgrade the user; a losing worker (two Celery
            # Beat/worker processes overlapping, or a manual + scheduled
            # run colliding) just matches zero documents and moves on,
            # instead of both racing to write the same user.
            claimed = Subscription.objects(id=sub.id, status="cancelled").update(
                set__status="expired", set__updated_at=now
            )
            if not claimed:
                lost_race += 1
                continue

            user = User.objects(id=sub.user_id).first()
            if user is None:
                # A Subscription with no matching User is a data-integrity
                # problem worth a human's attention, not just a silent
                # skip — the subscription itself is already correctly
                # marked "expired" above (that claim doesn't depend on
                # the user existing), so this orphan won't keep coming
                # back on every future run; it just won't self-heal
                # either. Log it distinctly from "lost the race" so it's
                # findable.
                logger.warning(
                    "expire_subscriptions: Subscription %s references "
                    "missing user_id=%s — subscription marked expired, "
                    "but no user record to downgrade or notify.",
                    sub.id,
                    sub.user_id,
                )
                orphaned += 1
                continue

            user.plan = "Free"
            user.plan_expires_at = None
            user.save()

            Notification(
                user_id=str(user.id),
                kind="pro_upsell",
                title=f"Your {sub.plan} access has ended",
                body=(
                    f"The {sub.plan} billing period you already paid for has finished, so "
                    "your account is back on the Free plan. Resubscribe any time "
                    "from your Profile."
                ),
            ).save()

            try:
                send_pro_expired_email(user.email, user.name.split(" ")[0], sub.plan)
            except Exception:
                # Never let an email provider hiccup stop the actual
                # downgrade — the in-app notification above already
                # covers it; this is a nice-to-have on top, not the
                # source of truth. Still needs to be visible in logs
                # though, since a real SMTP outage silently means nobody
                # gets this email until someone notices.
                logger.exception("Failed to send Pro-expired email to %s", user.email)

            expired += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired: {expired}, Lost race: {lost_race}, Orphaned: {orphaned}"
            )
        )