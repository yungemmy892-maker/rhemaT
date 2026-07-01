"""
Web Push delivery using py_vapid (for VAPID JWT signing) and requests (for
the HTTP POST to the push service). This avoids pywebpush's aiohttp
dependency, which fails to install on many platforms without a Rust/C
compiler toolchain available.
"""
import json
import os
from urllib.parse import urlparse

import requests
from django.conf import settings
from py_vapid import Vapid01

from .models import PushSubscription


class PushDeliveryError(Exception):
    pass


def _get_vapid() -> Vapid01 | None:
    key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not key:
        return None
    try:
        return Vapid01.from_raw(key.encode() if isinstance(key, str) else key)
    except Exception:
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
        "TTL": "86400",                       # deliver within 24 hours or drop
        "Authorization": vapid_headers["Authorization"],
        "Crypto-Key": vapid_headers["Crypto-Key"],
    }


def send_push_to_user(user_id: str, payload: dict) -> dict:
    """
    Sends a Web Push message to every browser subscription registered for
    this user. Returns {"sent": int, "expired": int}.

    Note: this implementation sends the payload as unencrypted JSON in the
    push body. The payload is therefore visible to the push service
    (Google FCM, Mozilla, Apple, etc.) — it must not contain private data.
    For end-to-end encryption (RFC 8291 / aes128gcm), a full implementation
    using the Web Push encryption spec would be needed; that requires the
    p256dh public key from the subscription and additional crypto primitives.
    For a devotional app whose notifications contain only verse references
    and short motivational text, plain (unauthenticated) push is acceptable.
    """
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
                timeout=10,
            )
            if resp.status_code in (404, 410):
                # Browser has unsubscribed / subscription is stale — remove it
                sub.delete()
                expired += 1
            elif resp.status_code in (200, 201, 202):
                sent += 1
            # Other failures (5xx, 400 auth issues) are transient — leave
            # the subscription in place so we retry on the next delivery.
        except requests.RequestException:
            pass  # Network error — treat as transient, keep subscription

    return {"sent": sent, "expired": expired}
