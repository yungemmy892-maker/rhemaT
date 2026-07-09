import datetime

from django.core.management.base import BaseCommand

from notifications.models import Notification
from users.models import User

from billing.models import Subscription
from billing.paystack import PaystackError, charge_authorization

MAX_RENEWAL_ATTEMPTS = 3


class Command(BaseCommand):
    help = "Auto-renews Pro subscriptions by charging the saved card via Paystack."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore the due-date and once-per-day checks (for manual testing).",
        )

    def handle(self, *args, **options):
        force = options["force"]
        now = datetime.datetime.utcnow()
        today = now.date()

        query = {"status": "active"}
        if not force:
            query["current_period_end__lte"] = now

        due_subs = list(Subscription.objects(**query))
        self.stdout.write(f"{len(due_subs)} active subscription(s) past their period end.")

        renewed = failed = skipped = 0

        for sub in due_subs:
            if not force and sub.last_renewal_attempt_date == today:
                skipped += 1
                continue

            if not sub.paystack_authorization_code:
                # Shouldn't normally happen (every successful charge stores
                # one) — without it we simply cannot auto-charge; the user
                # will notice Pro lapsed and can resubscribe manually.
                skipped += 1
                continue

            user = User.objects(id=sub.user_id).first()
            if user is None:
                skipped += 1
                continue

            sub.last_renewal_attempt_date = today

            try:
                result = charge_authorization(
                    email=user.email,
                    amount_kobo=sub.amount_kobo,
                    authorization_code=sub.paystack_authorization_code,
                    metadata={"user_id": str(user.id), "interval": sub.interval, "renewal": True},
                )
            except PaystackError as exc:
                self._handle_failure(sub, user, str(exc))
                failed += 1
                continue

            if result.get("status") != "success":
                self._handle_failure(sub, user, result.get("gateway_response") or "Charge declined")
                failed += 1
                continue

            days = 30 if sub.interval == "monthly" else 365
            new_period_end = now + datetime.timedelta(days=days)

            sub.renewal_attempts = 0
            sub.current_period_end = new_period_end
            sub.updated_at = now
            sub.save()

            user.plan = "Pro"
            user.plan_expires_at = new_period_end
            user.save()

            Notification(
                user_id=str(user.id),
                kind="pro_upsell",
                title="Pro subscription renewed",
                body=(
                    f"Your VerseID Pro subscription has been renewed for another "
                    f"{'month' if sub.interval == 'monthly' else 'year'}."
                ),
            ).save()
            renewed += 1

        self.stdout.write(
            self.style.SUCCESS(f"Renewed: {renewed}, Failed: {failed}, Skipped: {skipped}")
        )

    def _handle_failure(self, sub: Subscription, user: User, reason: str) -> None:
        sub.renewal_attempts = (sub.renewal_attempts or 0) + 1

        if sub.renewal_attempts >= MAX_RENEWAL_ATTEMPTS:
            sub.status = "past_due"
            sub.save()
            user.plan = "Free"
            user.plan_expires_at = None
            user.save()
            Notification(
                user_id=str(user.id),
                kind="pro_upsell",
                title="Pro subscription ended",
                body=(
                    "We couldn't renew your payment after several attempts, so your Pro access "
                    "has ended. You can resubscribe anytime from your Profile."
                ),
            ).save()
        else:
            sub.save()
            Notification(
                user_id=str(user.id),
                kind="pro_upsell",
                title="Payment failed",
                body=(
                    f"We couldn't renew your Pro subscription ({reason}). We'll try again — "
                    "please make sure your card has sufficient funds and hasn't expired."
                ),
            ).save()