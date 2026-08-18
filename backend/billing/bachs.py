import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BachsError(Exception):
    pass


def _headers(idempotency_key: str | None = None):
    headers = {
        "Authorization": f"Bearer {settings.BACHS_API_KEY}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _extract_error_detail(exc: requests.RequestException) -> str:
    """Bachs errors are always { detail, error_code, doc_url } (confirmed
    via the real OpenAPI spec) — pull the human-readable detail out when
    there's a response body, falling back to the raw exception string for
    network-level failures (timeout, DNS, connection refused) that never
    got a response body at all."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.json()
            return f"{body.get('error_code', '?')}: {body.get('detail', str(exc))}"
        except ValueError:
            pass
    return str(exc)


def create_checkout_session(
    email: str,
    name: str,
    product_id: str,
    metadata: dict,
    success_url: str,
    cancel_url: str,
    customer_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """
    Creates a Bachs checkout session for a recurring product and returns
    the session. Unlike Paystack, there's no separate "create subscription"
    call — completing checkout for a recurring product IS what creates the
    Subscription on Bachs's side (docs.bachs.io/guides/subscriptions/overview).

    `customer` MUST be a nested object, not a flat customer_email field —
    confirmed against the real CreateCheckoutSessionRequest schema. `name`
    is required alongside `email` for a new customer (NewCustomerRequest);
    pass `customer_id` instead to reuse an existing Bachs customer (e.g.
    Subscription.bachs_customer_id from an earlier subscription) rather
    than creating a duplicate customer record on every checkout attempt.

    `idempotency_key` should be the SAME value across retries of one
    logical checkout attempt (e.g. a double-tap on Subscribe), and a
    DIFFERENT value for a genuinely new attempt (e.g. the customer coming
    back after an earlier session expired) — reusing it too broadly would
    silently hand back a stale/expired session instead of a new one.
    """
    customer = {"customer_id": customer_id} if customer_id else {"email": email, "name": name}
    try:
        resp = requests.post(
            f"{settings.BACHS_BASE_URL}/v1/checkout-sessions",
            headers=_headers(idempotency_key),
            json={
                "customer": customer,
                "product_cart": [{"product_id": product_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        detail = _extract_error_detail(exc)
        logger.error(
            "Bachs create_checkout_session failed: email=%s product_id=%s error=%s",
            email,
            product_id,
            detail,
        )
        raise BachsError(detail) from exc


def checkout_url(session: dict) -> str:
    """Pulls the redirect URL out of a checkout-session response. Field
    name confirmed against the real OpenAPI spec's
    CreateCheckoutSessionResponse schema: `checkout_url`."""
    return session.get("checkout_url", "")


def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> dict:
    """
    Cancels a Bachs subscription — immediately, or at the end of the
    current paid period via cancel_at_period_end. VerseID always uses the
    latter, matching the existing Paystack cancel behavior: keep access
    until the period the customer already paid for actually ends.
    """
    idempotency_key = hashlib.sha256(
        f"cancel:{subscription_id}:{int(time.time() // 60)}".encode()
    ).hexdigest()
    try:
        resp = requests.post(
            f"{settings.BACHS_BASE_URL}/v1/subscriptions/{subscription_id}/cancel",
            headers=_headers(idempotency_key),
            json={"cancel_at_period_end": at_period_end},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        detail = _extract_error_detail(exc)
        logger.error(
            "Bachs cancel_subscription failed: subscription_id=%s error=%s",
            subscription_id,
            detail,
        )
        raise BachsError(detail) from exc


def verify_webhook_signature(
    payload_bytes: bytes, signature: str, timestamp: str, tolerance_seconds: int = 300
) -> bool:
    """
    Validates a Bachs webhook per docs.bachs.io/guides/webhooks/overview:
    HMAC-SHA256 of the string "{timestamp}.{raw_body}", signed with the
    webhook secret, compared against X-Bachs-Signature. timestamp comes
    from the X-Bachs-Timestamp header and must also be recent — without
    that check, a captured-but-still-validly-signed request could be
    replayed indefinitely.

    Built as bytes concatenation (not a decode/format/re-encode of
    payload_bytes) so this can't corrupt a raw body that isn't cleanly
    UTF-8 round-trippable — same reasoning as verifying against the raw
    request body before JSON parsing in the view itself.
    """
    if not settings.BACHS_WEBHOOK_SECRET:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}.".encode() + payload_bytes
    expected = hmac.new(
        settings.BACHS_WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)