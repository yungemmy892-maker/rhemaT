import datetime
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from mongoengine.errors import NotUniqueError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from users.models import User

from .models import Payment, PaystackEvent, Subscription
from .paystack import (
    initialize_transaction,
    verify_transaction,
    verify_webhook_signature,
)
from .serializers import InitiatePaymentSerializer, VerifyPaymentSerializer

logger = logging.getLogger(__name__)

NGN_PRICES = {
    "monthly": {
        "kobo": settings.PLAN_MONTHLY_KOBO,
        "label": "₦1,000/month",
        "naira": 1000,
    },
    "annual": {
        "kobo": settings.PLAN_ANNUAL_KOBO,
        "label": "₦9,000/year",
        "naira": 9000,
        "savings": "Save ₦3,000",
    },
}


def _now() -> datetime.datetime:
    """
    UTC "now" using Django's non-deprecated timezone-aware clock instead of
    the deprecated `datetime.datetime.utcnow()`, but with tzinfo stripped
    before it touches anything. Every DateTimeField written by MongoEngine
    across this whole codebase is naive UTC (the Mongo connection isn't
    configured with tz_aware=True — see config/settings.py), so comparing
    an aware `timezone.now()` directly against a value read back from a
    Subscription/User document would raise
    "can't compare offset-naive and offset-aware datetimes". Stripping
    tzinfo here keeps every read/write/comparison in this file consistent
    with that existing naive-UTC convention.
    """
    return dj_timezone.now().replace(tzinfo=None)


class PricingView(APIView):
    """GET /api/v1/billing/pricing/ — NGN plan prices (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "currency": "NGN",
                "symbol": "₦",
                "plans": NGN_PRICES,
                "freeLimit": User.FREE_DAILY_SEARCH_LIMIT,
            }
        )


class InitiatePaymentView(APIView):
    """
    POST /api/v1/billing/initiate/
    Body: { "interval": "monthly"|"annual", "callback_url": "..." }

    Returns { "authorization_url": "https://checkout.paystack.com/..." }
    which the frontend opens (redirect or popup) for card entry.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        interval = data["interval"]
        price = NGN_PRICES[interval]

        try:
            tx = initialize_transaction(
                email=request.user.email,
                amount_kobo=price["kobo"],
                metadata={
                    "user_id": str(request.user.id),
                    "interval": interval,
                    "cancel_action": data["callback_url"].replace(
                        "status=success", "status=cancelled"
                    ),
                },
                callback_url=data["callback_url"],
            )
        except Exception as exc:
            logger.error("Paystack initiate error: %s", exc)
            return Response(
                {
                    "error": {
                        "code": 502,
                        "message": "Payment gateway error. Please try again.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "authorization_url": tx["authorization_url"],
                "reference": tx["reference"],
                "amount_naira": price["naira"],
                "interval": interval,
            }
        )


class VerifyPaymentView(APIView):
    """
    POST /api/v1/billing/verify/
    Body: { "reference": "<paystack_reference>" }

    Called by the frontend after Paystack redirects back to callback_url.
    Verifies payment with Paystack and activates Pro if successful.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data["reference"]

        # Idempotency guard. Payment.reference is the durable, permanent
        # record that this exact Paystack transaction has already been
        # processed. Without this check, a double-tap on "Subscribe", a
        # browser back+resubmit, or the frontend retrying a slow response
        # could all call _activate_pro() more than once for the very same
        # charge. Checked first (before even calling Paystack) so a
        # request we already know is a repeat doesn't cost an extra
        # outbound verify call either.
        if Payment.objects(reference=reference).first():
            user = User.objects(id=request.user.id).first()
            return Response({"user": user.to_public_dict(), "status": "already_verified"})

        try:
            tx = verify_transaction(reference)
        except Exception as exc:
            logger.error("Paystack verify error: %s", exc)
            return Response(
                {
                    "error": {
                        "code": 502,
                        "message": "Could not verify payment. Please contact support.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if tx["status"] != "success":
            return Response(
                {
                    "error": {
                        "code": 402,
                        "message": f"Payment not completed (status: {tx['status']}).",
                    }
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        metadata = tx.get("metadata", {})
        interval = metadata.get("interval", "monthly")
        user_id = metadata.get("user_id", str(request.user.id))

        _activate_pro(user_id, interval, tx)
        _record_payment(reference, user_id, interval, tx.get("amount", 0))

        user = User.objects(id=request.user.id).first()
        return Response({"user": user.to_public_dict(), "status": "activated"})


class CancelSubscriptionView(APIView):
    """
    POST /api/v1/billing/cancel/ — marks the subscription as cancelled but
    does NOT downgrade the user immediately. The UI promises "You keep Pro
    until your billing ends", so `user.plan` and `user.plan_expires_at`
    are left untouched here; expire_subscriptions.py (run hourly) is what
    actually flips a cancelled-and-lapsed subscription over to Free once
    current_period_end has passed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        Subscription.objects(user_id=str(user.id)).update(set__status="cancelled")
        Notification(
            user_id=str(user.id),
            kind="pro_upsell",
            title="Pro subscription cancelled",
            body="Your Pro features will remain until the end of the billing period.",
        ).save()
        return Response(user.to_public_dict())


class PaystackWebhookView(APIView):
    """
    POST /api/v1/billing/webhook/
    Paystack sends signed POST events here for async subscription
    renewals, cancellations, and failures. Set this URL in your Paystack
    Dashboard > Settings > API Keys & Webhooks.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Paystack-Signature", "")
        if not verify_webhook_signature(request.body, signature):
            return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_id = payload.get("id") or payload.get("data", {}).get("id", "")
        event_type = payload.get("event", "")

        # Idempotency — skip duplicates
        if event_id and PaystackEvent.objects(event_id=str(event_id)).first():
            return HttpResponse(status=200)

        PaystackEvent(
            event_id=str(event_id), event_type=event_type, payload=payload
        ).save()

        data = payload.get("data", {})
        customer_code = data.get("customer", {}).get("customer_code")
        sub = Subscription.objects(
            paystack_subscription_code=data.get("subscription_code")
        ).first()
        user_id = sub.user_id if sub else None

        if event_type == "charge.success":
            metadata = data.get("metadata", {})
            uid = metadata.get("user_id") or user_id
            interval = metadata.get("interval", "monthly")
            charge_reference = data.get("reference", "")
            # Renewal charges (charge_renewals.py) already activate Pro and
            # send their own "renewed" notification synchronously right
            # after the charge succeeds — skip here to avoid a duplicate,
            # contradictory "Welcome to Pro 🎉" notification on a renewal.
            if uid and not metadata.get("renewal"):
                # This webhook can race — or simply duplicate-deliver, or
                # arrive after — the same charge already processed via
                # /billing/verify/. Payment.reference is the shared
                # idempotency ledger between both entry points, so a
                # reference that's already recorded is skipped entirely
                # rather than re-running _activate_pro().
                already_processed = bool(
                    charge_reference
                    and Payment.objects(reference=charge_reference).first()
                )
                if not already_processed:
                    _activate_pro(uid, interval, data)
                    if charge_reference:
                        _record_payment(
                            charge_reference, uid, interval, data.get("amount", 0)
                        )

        elif event_type in ("subscription.disable", "subscription.not_renew"):
            if sub:
                sub.status = "cancelled"
                sub.save()
                user = User.objects(id=sub.user_id).first()
                if user:
                    user.plan = "Free"
                    user.plan_expires_at = sub.current_period_end
                    user.save()

        elif event_type == "invoice.payment_failed":
            if user_id:
                Notification(
                    user_id=user_id,
                    kind="pro_upsell",
                    title="Payment failed",
                    body="We couldn't renew your Pro subscription — please update your payment details.",
                ).save()

        return HttpResponse(status=200)


def _record_payment(
    reference: str,
    user_id: str,
    interval: str,
    amount_kobo: int,
    gateway_status: str = "success",
) -> None:
    """
    Writes the permanent Payment ledger entry for a processed charge. This
    is what makes /billing/verify/ (and the charge.success webhook)
    idempotent — a unique index on `reference` means this is safe to call
    from more than one code path for the very same transaction (verify and
    the webhook can both observe the same charge); a second insert for an
    already-recorded reference is swallowed rather than raised, since by
    definition someone else already wrote the durable record this call was
    trying to create.
    """
    try:
        Payment(
            reference=reference,
            user_id=user_id,
            interval=interval,
            amount_kobo=amount_kobo,
            gateway="paystack",
            status=gateway_status,
            paid_at=_now(),
        ).save(force_insert=True)
    except NotUniqueError:
        pass


def _activate_pro(user_id: str, interval: str, tx_data: dict):
    """
    Shared helper: marks user as Pro and upserts the Subscription record.

    Notification is idempotent. This gets called from more than one place
    (a fresh /billing/verify/, the charge.success webhook, and — via those
    — potentially more than once for what's effectively the same
    activation) so unconditionally sending "Welcome to VerseID Pro" every
    time would spam a duplicate "welcome" notification for something that
    isn't new. It only notifies when this activation is a genuine
    (re)activation — no existing subscription, one that wasn't active, or
    one whose period had already lapsed — not a no-op re-run against an
    already-active subscription.
    """
    user = User.objects(id=user_id).first()
    if user is None:
        return

    now = _now()
    days = 30 if interval == "monthly" else 365
    expires_at = now + datetime.timedelta(days=days)

    existing_sub = Subscription.objects(user_id=user_id).first()
    should_notify = (
        existing_sub is None
        or existing_sub.status != "active"
        or existing_sub.current_period_end is None
        or existing_sub.current_period_end < now
    )

    user.plan = "Pro"
    user.plan_expires_at = expires_at
    user.save()

    Subscription.objects(user_id=user_id).upsert_one(
        set__paystack_customer_code=tx_data.get("customer", {}).get(
            "customer_code", ""
        ),
        set__paystack_subscription_code=tx_data.get("subscription_code", ""),
        set__paystack_authorization_code=tx_data.get("authorization", {}).get(
            "authorization_code", ""
        ),
        set__interval=interval,
        set__amount_kobo=tx_data.get("amount", 0),
        set__status="active",
        set__current_period_end=expires_at,
        set__last_reference=tx_data.get("reference", ""),
        set__updated_at=now,
    )

    if should_notify:
        Notification(
            user_id=user_id,
            kind="pro_upsell",
            title="Welcome to VerseID Pro 🎉",
            body="Unlimited searches and all premium features are now unlocked.",
        ).save()
