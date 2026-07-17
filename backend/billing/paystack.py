import hashlib
import hmac

import requests
from django.conf import settings

PAYSTACK_BASE = "https://api.paystack.co"


class PaystackError(Exception):
    pass


class PaystackDuplicateReference(PaystackError):
    """
    Raised when a reference was already used on a previous request. This
    means the charge may already have gone through in a prior (possibly
    crashed/interrupted) attempt — callers must verify_transaction() to
    find out what actually happened before treating this as a failure or
    retrying with a new reference.
    """


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


def charge_authorization(
    email: str,
    amount_kobo: int,
    authorization_code: str,
    metadata: dict,
    reference: str,
) -> dict:
   
    try:
        resp = requests.post(
            f"{PAYSTACK_BASE}/transaction/charge_authorization",
            headers=_headers(),
            json={
                "email": email,
                "amount": amount_kobo,
                "authorization_code": authorization_code,
                "currency": "NGN",
                "metadata": metadata,
                "reference": reference,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise PaystackError(str(exc)) from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise PaystackError(f"Non-JSON response from Paystack (HTTP {resp.status_code})") from exc

    # Paystack always returns HTTP 200 for a charge request that was
    # *accepted and attempted* — a declined card, insufficient funds, etc.
    # show up as data.status == "failed" within a 200, and callers check
    # that separately. A non-2xx / status:false response here means the
    # REQUEST ITSELF was rejected (bad params, duplicate reference) before
    # any charge attempt was made.
    if resp.status_code >= 400 or body.get("status") is False:
        message = body.get("message", "")
        code = body.get("code", "")
        # Confirmed against Paystack's docs: the "Duplicate Transaction
        # Reference" error's message text is exactly
        # "This transaction reference has already been used on this
        # integration." The exact `code` string for this case isn't
        # published anywhere we could verify, so `duplicate_reference` is
        # a best guess (matches their snake_case convention) rather than a
        # confirmed value — trigger this once in a sandbox and check the
        # logged body below to confirm/correct it.
        if code == "duplicate_reference" or "already been used" in message.lower():
            raise PaystackDuplicateReference(message or code)
        raise PaystackError(
            f"{message or code or 'Unknown error'} "
            f"(HTTP {resp.status_code}, code={code!r}, raw={body!r})"
        )

    return body["data"]


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