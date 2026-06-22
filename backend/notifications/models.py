import datetime
import uuid

import mongoengine as me

# Matches the frontend's existing hardcoded notification "kinds" in
# app.notifications.tsx (verse-of-day, saved-to-library, pro-upsell,
# new-voice, streak) — each kind maps client-side to a specific icon/color
# tint, which is presentational and stays in the frontend rather than
# being sent from the backend.
NOTIFICATION_KINDS = (
    "verse_of_day",
    "saved_to_library",
    "pro_upsell",
    "new_voice",
    "streak",
)


def _gen_id():
    return uuid.uuid4().hex


class Notification(me.Document):
    """A single item in a user's notification feed."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    kind = me.StringField(choices=NOTIFICATION_KINDS, required=True)
    title = me.StringField(required=True)
    body = me.StringField(required=True)
    read = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "notifications",
        "indexes": ["user_id", "-created_at"],
        "ordering": ["-created_at"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "unread": not self.read,
            "createdAt": int(self.created_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000),
        }


class PushSubscription(me.Document):
    """
    A browser's Web Push subscription (from the PushManager API), used to
    deliver the daily verse notification even when the app/tab is closed.
    One user can have several (one per device/browser).
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    endpoint = me.StringField(required=True, unique=True)
    p256dh = me.StringField(required=True)
    auth = me.StringField(required=True)
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "push_subscriptions",
        "indexes": ["user_id", "endpoint"],
    }

    def to_subscription_info(self):
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }
