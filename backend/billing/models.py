import datetime
import uuid

import mongoengine as me


def _gen_id():
    return uuid.uuid4().hex


BILLING_INTERVALS = ("monthly", "annual")


class Subscription(me.Document):
    """
    Tracks the active Paystack subscription for a Pro user.
    Created/updated by webhook events from Paystack.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True, unique=True)
    plan = me.StringField(choices=("Pro", "Family"), default="Pro")
    paystack_customer_code = me.StringField()
    paystack_subscription_code = me.StringField()
    paystack_authorization_code = me.StringField()
    interval = me.StringField(choices=BILLING_INTERVALS, default="monthly")
    amount_kobo = me.IntField()  # actual charged amount in kobo
    status = me.StringField(default="active")  # active | past_due | cancelled
    current_period_end = me.DateTimeField()
    # Automatic renewal tracking (management/commands/charge_renewals.py) —
    # this integration charges the saved card directly via Paystack's
    # Transactions API rather than their native Plans/Subscriptions API, so
    # nothing renews automatically on Paystack's side; this command IS the
    # renewal mechanism and these fields drive its retry policy.
    renewal_attempts = me.IntField(default=0)
    last_renewal_attempt_date = me.DateField(null=True)
    # Debugging aid — the most recent Paystack transaction reference this
    # subscription was activated/renewed from (initial charge or a
    # charge_renewals.py renewal). Not used for any logic; just makes it
    # possible to look at a Subscription document and immediately know
    # which Paystack transaction to go check when something looks off.
    last_reference = me.StringField()
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "subscriptions",
        "indexes": ["user_id", "paystack_subscription_code"],
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


PAYMENT_STATUSES = ("success", "failed")


class Payment(me.Document):
    """
    Permanent, append-only record of every successful (and, best-effort,
    failed) Paystack charge — the initial subscribe AND every renewal.

    This is the idempotency ledger for /billing/verify/: that endpoint used
    to have no durable record that a given `reference` had already been
    processed, so a double-submit (double-tap, browser back+resubmit, retry
    after a slow response) could call _activate_pro() more than once for
    the same charge. `reference` is unique so a second insert attempt for
    the same Paystack transaction fails fast instead of silently
    re-activating Pro.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    reference = me.StringField(required=True, unique=True)
    user_id = me.StringField(required=True)
    plan = me.StringField(choices=("Pro", "Family"), default="Pro")
    interval = me.StringField(choices=BILLING_INTERVALS, required=True)
    amount_kobo = me.IntField(required=True)
    gateway = me.StringField(default="paystack")
    status = me.StringField(choices=PAYMENT_STATUSES, default="success")
    paid_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "payments",
        "indexes": ["reference", "user_id"],
        "strict": False,
    }