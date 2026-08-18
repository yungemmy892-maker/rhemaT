import datetime
import uuid

import mongoengine as me


def _gen_id():
    return uuid.uuid4().hex


BILLING_INTERVALS = ("monthly", "annual")


class Subscription(me.Document):
    """
    Tracks the active subscription for a Pro/Family user — Paystack (NGN)
    or Bachs (USD). Created/updated by webhook events from whichever
    gateway the subscription is on.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True, unique=True)
    plan = me.StringField(choices=("Pro", "Family"), default="Pro")
    gateway = me.StringField(choices=("paystack", "bachs"), default="paystack")
    # Paystack (NGN)
    paystack_customer_code = me.StringField()
    paystack_subscription_code = me.StringField()
    paystack_authorization_code = me.StringField()
    # Bachs (USD) — Bachs owns recurring collection itself (unlike
    # Paystack — see renewal_attempts below), so these two IDs exist
    # purely to look the subscription up on Bachs's side (e.g. to cancel
    # it), not to drive any renewal logic locally.
    bachs_customer_id = me.StringField()
    bachs_subscription_id = me.StringField()
    interval = me.StringField(choices=BILLING_INTERVALS, default="monthly")
    amount_kobo = me.IntField()  # gateway == "paystack"
    amount_usd_cents = me.IntField()  # gateway == "bachs"
    status = me.StringField(default="active")  # active | past_due | unpaid | cancelled
    current_period_end = me.DateTimeField()
    # Automatic renewal tracking (management/commands/charge_renewals.py) —
    # Paystack-only. This integration charges the saved card directly via
    # Paystack's Transactions API rather than their native Plans/
    # Subscriptions API, so nothing renews automatically on Paystack's
    # side; that command IS the renewal mechanism and these fields drive
    # its retry policy. Bachs subscriptions renew on Bachs's own side —
    # these stay at their defaults (0 / null) for gateway == "bachs" rows,
    # and charge_renewals.py's query explicitly excludes them.
    renewal_attempts = me.IntField(default=0)
    last_renewal_attempt_date = me.DateField(null=True)
    # Debugging aid — the most recent transaction/charge reference this
    # subscription was activated/renewed from. Not used for any logic;
    # just makes it possible to look at a Subscription document and
    # immediately know which Paystack transaction or Bachs collection to
    # go check when something looks off.
    last_reference = me.StringField()
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "subscriptions",
        "indexes": ["user_id", "paystack_subscription_code", "bachs_subscription_id"],
        "strict": False,
    }


class PaystackEvent(me.Document):
    """Idempotency log of received Paystack webhook events."""

    id = me.StringField(primary_key=True, default=_gen_id)
    event_id = me.StringField(unique=True)
    event_type = me.StringField()
    payload = me.DictField()
    processed_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {"collection": "paystack_events", "indexes": ["event_id"], "strict": False}


class BachsEvent(me.Document):
    """
    Idempotency log of received Bachs webhook events — mirrors
    PaystackEvent exactly. Same problem (Bachs guarantees at-least-once
    delivery, so the same event can arrive more than once), same fix:
    check-then-insert on a unique event_id, with the insert itself (via
    save(force_insert=True) + catching NotUniqueError) as the actual race
    guard, not the check.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    event_id = me.StringField(unique=True)  # Bachs webhook envelope's top-level `id`
    event_type = me.StringField()  # Bachs webhook envelope's `type`
    payload = me.DictField()
    processed_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {"collection": "bachs_events", "indexes": ["event_id"], "strict": False}


PAYMENT_STATUSES = ("success", "failed")


class Payment(me.Document):
    """
    Permanent, append-only record of every successful (and, best-effort,
    failed) charge — Paystack or Bachs, the initial subscribe AND every
    renewal.

    This is the idempotency ledger for /billing/verify/ and the Bachs
    webhook handler: neither endpoint has any other durable record that a
    given `reference` had already been processed, so a double-submit
    (double-tap, browser back+resubmit, retry after a slow response, or a
    duplicate webhook delivery) could call activate_plan()/
    sync_bachs_subscription() more than once for the same charge.
    `reference` is unique so a second insert attempt for the same
    transaction fails fast instead of silently re-activating a plan.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    reference = me.StringField(required=True, unique=True)
    user_id = me.StringField(required=True)
    plan = me.StringField(choices=("Pro", "Family"), default="Pro")
    interval = me.StringField(choices=BILLING_INTERVALS, required=True)
    gateway = me.StringField(default="paystack")
    amount_kobo = me.IntField()  # gateway == "paystack"
    amount_usd_cents = me.IntField()  # gateway == "bachs"
    status = me.StringField(choices=PAYMENT_STATUSES, default="success")
    paid_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "payments",
        "indexes": ["reference", "user_id"],
        "strict": False,
    }