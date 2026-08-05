import json
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from py_vapid import Vapid01

from .models import PushSubscription

logger = logging.getLogger(__name__)


class PushDeliveryError(Exception):
    pass


def _get_vapid() -> Vapid01 | None:
    key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not key:
        return None
    try:
        return Vapid01.from_raw(key.encode() if isinstance(key, str) else key)
    except Exception:
        logger.exception("Failed to load VAPID key")
        return None


def _build_headers(endpoint: str, vapid: Vapid01) -> dict:
    """Build the VAPID Authorization and Crypto-Key headers for a push POST."""
    parsed = urlparse(endpoint)
    audience = f"{parsed.scheme}://{parsed.netloc}"
    claim = {
        "sub": getattr(settings, "VAPID_CLAIM_EMAIL", "mailto:admin@example.com"),
        "aud": audience,
    }
    vapid_headers = vapid.sign(claim)
    return {
        "Content-Type": "application/json",
        "TTL": "86400",  # deliver within 24 hours or drop
        "Authorization": vapid_headers["Authorization"],
        "Crypto-Key": vapid_headers["Crypto-Key"],
    }


def send_push_to_user(user_id: str, payload: dict) -> dict:
    vapid = _get_vapid()
    if vapid is None:
        return {"sent": 0, "expired": 0, "error": "VAPID_PRIVATE_KEY not configured"}

    subs = list(PushSubscription.objects(user_id=user_id))
    sent = 0
    expired = 0

    for sub in subs:
        try:
            headers = _build_headers(sub.endpoint, vapid)
            resp = requests.post(
                sub.endpoint,
                headers=headers,
                data=json.dumps(payload).encode(),
                # Separate connect/read timeouts instead of one shared value —
                # bounds worst case per subscription to 8s instead of ~20s,
                # so one slow/stale endpoint can't stall a user's whole run.
                timeout=(3.5, 8),
            )
            if resp.status_code in (404, 410):
                # Browser has unsubscribed / subscription is stale — remove it
                sub.delete()
                expired += 1
            elif resp.status_code in (200, 201, 202):
                sent += 1
            else:
                # Other failures (5xx, 400 auth issues) are transient — leave
                # the subscription in place so we retry on the next delivery.
                logger.warning(
                    "Push to %s returned %s for user %s",
                    sub.endpoint, resp.status_code, user_id,
                )
        except requests.RequestException as exc:
            # Network error — treat as transient, keep subscription, but log
            # it so a systemic outage (bad VAPID key, DNS, etc.) is visible
            # instead of silently showing up as a low push count.
            logger.warning("Push delivery error for user %s: %s", user_id, exc)

    return {"sent": sent, "expired": expired}