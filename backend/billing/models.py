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
    paystack_customer_code = me.StringField()
    paystack_subscription_code = me.StringField()
    paystack_authorization_code = me.StringField()
    interval = me.StringField(choices=BILLING_INTERVALS, default="monthly")
    amount_kobo = me.IntField()           # actual charged amount in kobo
    status = me.StringField(default="active")   # active | paused | cancelled
    current_period_end = me.DateTimeField()
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "subscriptions",
        "indexes": ["user_id", "paystack_subscription_code"],
    }


class PaystackEvent(me.Document):
    """Idempotency log of received Paystack webhook events."""

    id = me.StringField(primary_key=True, default=_gen_id)
    event_id = me.StringField(unique=True)
    event_type = me.StringField()
    payload = me.DictField()
    processed_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {"collection": "paystack_events", "indexes": ["event_id"]}
