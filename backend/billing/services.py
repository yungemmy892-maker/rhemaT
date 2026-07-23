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
    interval: str,
    amount_kobo: int,
    gateway_status: str = "success",
) -> bool:
    """
    Writes the permanent Payment ledger entry for a processed charge —
    the initial subscribe (verify endpoint or webhook) AND every renewal
    (charge_renewals.py).
    """
    try:
        Payment(
            reference=reference,
            user_id=user_id,
            interval=interval,
            amount_kobo=amount_kobo,
            gateway="paystack",
            status=gateway_status,
            paid_at=now_utc(),
        ).save(force_insert=True)
        return True
    except NotUniqueError:
        return False


def activate_pro(user_id: str, interval: str, tx_data: dict) -> None:
    """
    Shared helper: marks user as Pro and upserts the Subscription record.
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

    user.plan = "Pro"
    user.plan_expires_at = expires_at
    user.save()

    Subscription.objects(user_id=user_id).upsert_one(
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
            title="Welcome to VerseID Pro 🎉",
            body="Unlimited searches and all premium features are now unlocked.",
        ).save()
