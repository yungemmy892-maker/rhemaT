import datetime
import logging

from django.core.management.base import BaseCommand

from notifications.models import Notification
from users.models import User

from billing.models import Subscription
from billing.paystack import (
    PaystackError,
    PaystackDuplicateReference,
    charge_authorization,
    verify_transaction,
)
from billing.services import now_utc, record_payment

logger = logging.getLogger(__name__)

MAX_RENEWAL_ATTEMPTS = 3


class Command(BaseCommand):
    help = "Auto-renews Pro and Family subscriptions by charging the saved card via Paystack."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore the due-date and once-per-day checks (for manual testing).",
        )

    def handle(self, *args, **options):
        force = options["force"]
        now = now_utc()
        today = now.date()

        # gateway="paystack" is load-bearing, not incidental: Bachs
        # subscriptions renew on Bachs's own side (that's the whole
        # reason this command exists for Paystack in the first place —
        # see Subscription.renewal_attempts' comment). Without this
        # filter, a Bachs row would match "status": "active" just as
        # well as a Paystack one, and this command would try to charge
        # it via paystack_authorization_code, which a Bachs-originated
        # subscription was never given.
        query = {"status": "active", "gateway": "paystack"}
        if not force:
            query["current_period_end__lte"] = now

        due_subs = list(Subscription.objects(**query))
        self.stdout.write(
            f"{len(due_subs)} active subscription(s) past their period end."
        )

        renewed = failed = skipped = 0

        for sub in due_subs:
            if not force and sub.last_renewal_attempt_date == today:
                skipped += 1
                continue

            # M5: atomically claim today's renewal-attempt slot before doing
            # any work. The old check-then-write let two workers both pass
            # the "not attempted today" check before either wrote, which can
            # double-charge a card under multi-worker deployment. This
            # conditional update only matches (and modifies) a document that
            # still needs today's attempt, so a losing worker's update simply
            # matches zero documents instead of racing.
            if not force:
                claimed = Subscription.objects(
                    id=sub.id, last_renewal_attempt_date__ne=today
                ).update(set__last_renewal_attempt_date=today)
                if not claimed:
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

            # Keep the in-memory object consistent with the atomic claim
            # above (already persisted) so the subsequent sub.save() calls
            # below don't clobber it with a stale value.
            sub.last_renewal_attempt_date = today

            # Reference is tied to the BILLING PERIOD being renewed, not to
            # today's date. It only changes once current_period_end is
            # actually advanced further down. This means any retry of this
            # same renewal — whether seconds later or a day later, if the
            # process crashes after charging but before saving — reuses the
            # exact same reference. Paystack rejects a reused reference
            # instead of charging again, which is what makes this
            # idempotent rather than just "less likely to double-charge."
            reference = (
                f"renewal_{sub.id}_"
                f"{sub.current_period_end.strftime('%Y%m%dT%H%M%S')}"
            )

            try:
                result = charge_authorization(
                    email=user.email,
                    amount_kobo=sub.amount_kobo,
                    authorization_code=sub.paystack_authorization_code,
                    metadata={
                        "user_id": str(user.id),
                        "plan": sub.plan,
                        "interval": sub.interval,
                        "renewal": True,
                    },
                    reference=reference,
                )
            except PaystackDuplicateReference:
                # A prior attempt (possibly one that crashed right after
                # charging) already sent this exact charge to Paystack.
                # Find out what actually happened instead of assuming
                # failure and retrying with a new reference.
                try:
                    verified = verify_transaction(reference)
                except PaystackError as exc:
                    self._handle_failure(
                        sub, user, f"Could not verify prior attempt: {exc}"
                    )
                    failed += 1
                    continue

                if verified.get("status") != "success":
                    self._handle_failure(
                        sub,
                        user,
                        "Prior renewal attempt unresolved — needs manual review",
                    )
                    failed += 1
                    continue
                result = verified
            except PaystackError as exc:
                self._handle_failure(sub, user, str(exc))
                failed += 1
                continue

            if result.get("status") != "success":
                self._handle_failure(
                    sub, user, result.get("gateway_response") or "Charge declined"
                )
                failed += 1
                continue

            days = 30 if sub.interval == "monthly" else 365
            # Anchor the new period on whichever is later: now, or the
            # period's existing end date. A renewal charge that runs a bit
            # early or a bit late (cron jitter, a retry that succeeds a
            # day after the first attempt) must not simply add `days` from
            # `now` — that would silently discard whatever time was left
            # on the subscription the user already paid for.
            base = max(now, sub.current_period_end)
            new_period_end = base + datetime.timedelta(days=days)

            try:
                # Compare-and-swap, not a plain sub.save(). This is the
                # actual guard against the PaystackDuplicateReference
                # recovery path above being reached concurrently by two
                # processes for the exact same renewal reference (a
                # redelivered Celery task, an overlapping manual --force
                # run) — only an update that still matches the OLD
                # current_period_end applies; a losing process's update
                # matches zero documents, so it can back out here instead
                # of double-extending the period and sending a second
                # "renewed" notification on top of the winner's.
                claimed_finalize = Subscription.objects(
                    id=sub.id, current_period_end=sub.current_period_end
                ).update(
                    set__renewal_attempts=0,
                    set__current_period_end=new_period_end,
                    set__updated_at=now,
                    set__last_reference=reference,
                )
                if not claimed_finalize:
                    skipped += 1
                    continue

                # Audit-trail entry for this renewal charge — the same
                # ledger /billing/verify/ and the webhook write to (see
                # billing/services.py). Best-effort here: a duplicate
                # insert is expected and NOT an error (e.g. a retry
                # recovering from a prior crash reuses the identical
                # reference — see the crash-recovery comment below), since
                # the compare-and-swap above, not this call, is what
                # actually decided whether this process gets to finalize.
                record_payment(
                    reference,
                    str(user.id),
                    sub.plan,
                    sub.interval,
                    gateway="paystack",
                    amount_kobo=sub.amount_kobo,
                )

                user.plan = sub.plan
                user.plan_expires_at = new_period_end
                user.save()

                Notification(
                    user_id=str(user.id),
                    kind="pro_upsell",
                    title=f"{sub.plan} subscription renewed",
                    body=(
                        f"Your VerseID {sub.plan} subscription has been renewed for another "
                        f"{'month' if sub.interval == 'monthly' else 'year'}."
                    ),
                ).save()
                renewed += 1
            except Exception:
                # Paystack has ALREADY charged the customer at this point,
                # and — if the compare-and-swap above succeeded before
                # this raised — Subscription.current_period_end may
                # already be advanced too, even though user.plan/
                # plan_expires_at or the notification below it didn't
                # finish. Don't swallow this into "failed" bookkeeping;
                # it needs a human to reconcile this specific user, since
                # a subscription that no longer looks "due" won't be
                # picked up for automatic retry on the next run.
                logger.critical(
                    "PAYSTACK CHARGED sub=%s user=%s amount_kobo=%s reference=%s "
                    "but a DB write failed partway through finalizing the "
                    "renewal — verify Subscription/User state for this user "
                    "manually.",
                    sub.id,
                    user.id,
                    sub.amount_kobo,
                    reference,
                    exc_info=True,
                )
                raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Renewed: {renewed}, Failed: {failed}, Skipped: {skipped}"
            )
        )

    def _handle_failure(self, sub: Subscription, user: User, reason: str) -> None:
        sub.renewal_attempts = (sub.renewal_attempts or 0) + 1
        is_first_attempt = sub.renewal_attempts == 1

        if sub.renewal_attempts >= MAX_RENEWAL_ATTEMPTS:
            # Final retry — always notify. This is the user's last chance
            # to know their Pro access actually ended, not just that one
            # more charge attempt failed.
            sub.status = "past_due"
            sub.save()
            user.plan = "Free"
            user.plan_expires_at = None
            user.save()
            Notification(
                user_id=str(user.id),
                kind="pro_upsell",
                title=f"{sub.plan} subscription ended",
                body=(
                    f"We couldn't renew your payment after several attempts, so your {sub.plan} access "
                    "has ended. You can resubscribe anytime from your Profile."
                ),
            ).save()
        else:
            sub.save()
            # Only notify on the FIRST failed attempt. Repeating "Payment
            # failed" on every intermediate retry is noisy and tells the
            # user nothing new — the next thing worth surfacing is either
            # a successful renewal (silent recovery) or the final
            # "Pro subscription ended" notice above once retries run out.
            if is_first_attempt:
                Notification(
                    user_id=str(user.id),
                    kind="pro_upsell",
                    title="Payment failed",
                    body=(
                        f"We couldn't renew your {sub.plan} subscription ({reason}). We'll try again - "
                        "please make sure your card has sufficient funds and hasn't expired."
                    ),
                ).save()