import json

from django.conf import settings
from pywebpush import WebPushException, webpush

from .models import PushSubscription


def send_push_to_user(user_id: str, payload: dict) -> dict:
    """
    Sends a Web Push message to every subscription registered for this
    user. Returns {"sent": int, "expired": int} — "expired" subscriptions
    (410 Gone / 404 from the push service, meaning the browser unsubscribed
    or the endpoint is stale) are deleted automatically.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return {"sent": 0, "expired": 0, "error": "VAPID keys not configured"}

    subs = PushSubscription.objects(user_id=user_id)
    sent = 0
    expired = 0

    for sub in subs:
        try:
            webpush(
                subscription_info=sub.to_subscription_info(),
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL},
            )
            sent += 1
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                sub.delete()
                expired += 1
            # Other failures (network blips, malformed payload) are not
            # treated as "this subscription is dead" and are left in place.

    return {"sent": sent, "expired": expired}
