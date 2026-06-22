import hashlib
import hmac
import json

import requests
from django.conf import settings

PAYSTACK_BASE = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(email: str, amount_kobo: int, metadata: dict, callback_url: str) -> dict:
    """
    Creates a Paystack transaction and returns the authorization URL the
    frontend redirects to for payment.
    """
    try:
        resp = requests.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            headers=_headers(),
            json={
                "email": email,
                "amount": amount_kobo,
                "currency": "NGN",
                "metadata": metadata,
                "callback_url": callback_url,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["data"]
    except requests.RequestException as exc:
        raise PaystackError(str(exc)) from exc


def verify_transaction(reference: str) -> dict:
    """Verifies a completed Paystack transaction by its reference."""
    try:
        resp = requests.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["data"]
    except requests.RequestException as exc:
        raise PaystackError(str(exc)) from exc


def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    """
    Validates that the webhook request genuinely came from Paystack by
    comparing the X-Paystack-Signature header against an HMAC-SHA512
    digest of the raw request body signed with the secret key.
    """
    if not settings.PAYSTACK_SECRET_KEY:
        return False
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        payload_bytes,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
