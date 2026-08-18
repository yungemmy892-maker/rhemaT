import datetime
import logging

from django.utils import timezone as dj_timezone
from mongoengine.errors import NotUniqueError

from notifications.models import Notification
from users.models import User

from .models import Payment, Subscription

logger = logging.getLogger(__name__)


def now_utc() -> datetime.datetime:
    return dj_timezone.now().replace(tzinfo=None)


def record_payment(
    reference: str,
    user_id: str,
    plan: str,
    interval: str,
    gateway: str = "paystack",
    amount_kobo: int | None = None,
    amount_usd_cents: int | None = None,
    gateway_status: str = "success",
) -> bool:
    """
    Writes the permanent Payment ledger entry for a processed charge — the
    initial subscribe (verify endpoint or webhook, either gateway) AND
    every renewal (charge_renewals.py for Paystack; Bachs renews itself,
    landing here via BachsWebhookView on each collection.succeeded).
    """
    try:
        Payment(
            reference=reference,
            user_id=user_id,
            plan=plan,
            interval=interval,
            gateway=gateway,
            amount_kobo=amount_kobo,
            amount_usd_cents=amount_usd_cents,
            status=gateway_status,
            paid_at=now_utc(),
        ).save(force_insert=True)
        return True
    except NotUniqueError:
        return False


def activate_plan(user_id: str, plan: str, interval: str, tx_data: dict) -> None:
    """
    Shared helper: marks user as Pro or Family and upserts the
    Subscription record. `plan` is "Pro" or "Family" — everything else
    (period math, idempotency, upsert shape) is identical between them.
    """
    user = User.objects(id=user_id).first()
    if user is None:
        return

    now = now_utc()
    days = 30 if interval == "monthly" else 365
    expires_at = now + datetime.timedelta(days=days)

    existing_sub = Subscription.objects(user_id=user_id).first()
    should_notify = (
        existing_sub is None
        or existing_sub.status != "active"
        or existing_sub.current_period_end is None
        or existing_sub.current_period_end < now
    )

    user.plan = plan
    user.plan_expires_at = expires_at
    user.save()

    Subscription.objects(user_id=user_id).upsert_one(
        set__plan=plan,
        set__paystack_customer_code=tx_data.get("customer", {}).get(
            "customer_code", ""
        ),
        set__paystack_subscription_code=tx_data.get("subscription_code", ""),
        set__paystack_authorization_code=tx_data.get("authorization", {}).get(
            "authorization_code", ""
        ),
        set__interval=interval,
        set__amount_kobo=tx_data.get("amount", 0),
        set__status="active",
        set__current_period_end=expires_at,
        set__last_reference=tx_data.get("reference", ""),
        set__updated_at=now,
    )

    if should_notify:
        Notification(
            user_id=user_id,
            kind="pro_upsell",
            title=f"Welcome to VerseID {plan} 🎉",
            body=(
                "Every member of your family now has unlimited searches and all "
                "translations unlocked."
                if plan == "Family"
                else "Unlimited searches and all premium features are now unlocked."
            ),
        ).save()


def sync_bachs_subscription(user_id: str, plan: str, subscription_data: dict) -> None:
    """
    Mirrors a Bachs subscription object into the local User/Subscription
    state. Called from BachsWebhookView on customer.subscription.created
    and customer.subscription.updated.

    Deliberately a full sync, not a delta: every field is overwritten from
    whatever Bachs just sent, rather than trying to interpret what changed.
    Bachs is the source of truth for its own subscription state — this
    just keeps the local mirror honest, the same principle as
    expire_subscriptions.py trusting current_period_end rather than
    tracking its own countdown.

    Unlike activate_plan() (Paystack), this does NOT unconditionally set
    user.plan/plan_expires_at — a subscription.updated carrying a
    "past_due" or "unpaid" status should NOT revoke access itself; Bachs
    is still retrying the charge, and expire_subscriptions.py (keyed off
    current_period_end, not status) is what actually removes access once
    the paid-for period has genuinely run out. This avoids yanking access
    mid-retry over a single failed attempt.
    """
    user = User.objects(id=user_id).first()
    if user is None:
        return

    now = now_utc()
    status = subscription_data.get("status", "active")
    current_period_end_raw = subscription_data.get("current_period_end")
    current_period_end = _parse_bachs_timestamp(current_period_end_raw) or now

    existing_sub = Subscription.objects(user_id=user_id).first()
    should_notify = (
        existing_sub is None
        or existing_sub.status != "active"
        or existing_sub.current_period_end is None
        or existing_sub.current_period_end < now
    )

    if status == "active":
        user.plan = plan
        user.plan_expires_at = current_period_end
        user.save()

    Subscription.objects(user_id=user_id).upsert_one(
        set__plan=plan,
        set__gateway="bachs",
        set__bachs_customer_id=subscription_data.get("customer", {}).get("customer_id", ""),
        set__bachs_subscription_id=subscription_data.get("id", ""),
        set__interval=(subscription_data.get("billing_cycle", {}) or {}).get(
            "interval", "monthly"
        ),
        set__amount_usd_cents=_dollars_to_cents(subscription_data.get("amount")),
        set__status=status,
        set__current_period_end=current_period_end,
        set__last_reference=subscription_data.get("id", ""),
        set__updated_at=now,
    )

    if should_notify and status == "active":
        Notification(
            user_id=user_id,
            kind="pro_upsell",
            title=f"Welcome to VerseID {plan} 🎉",
            body=(
                "Every member of your family now has unlimited searches and all "
                "translations unlocked."
                if plan == "Family"
                else "Unlimited searches and all premium features are now unlocked."
            ),
        ).save()


def _parse_bachs_timestamp(value) -> datetime.datetime | None:
    """Bachs timestamps are ISO 8601 strings (e.g. "2026-09-14T00:00:00Z").
    Not independently confirmed against a live payload in this pass — if
    Bachs actually sends unix epoch seconds/ms instead, this needs a
    one-line fix; logged rather than silently swallowed so a format
    mismatch is visible instead of quietly leaving current_period_end
    wrong."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    except (ValueError, TypeError) as exc:
        logger.error("Could not parse Bachs timestamp %r: %s", value, exc)
        return None


def _dollars_to_cents(amount) -> int | None:
    """Bachs money is a decimal string ("29.00"), never minor units —
    converted to integer cents here so internal storage stays consistent
    with amount_kobo's integer-minor-units convention rather than mixing
    representations across gateways."""
    if amount is None:
        return None
    try:
        return round(float(amount) * 100)
    except (ValueError, TypeError) as exc:
        logger.error("Could not parse Bachs amount %r: %s", amount, exc)
        return None