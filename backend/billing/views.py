import json
import logging

from django.conf import settings
from django.http import HttpResponse
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
from .services import activate_pro, record_payment

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

        # Fast-path idempotency check. Payment.reference is the durable,
        # permanent record that this exact Paystack transaction has
        # already been processed. This check alone can't fully prevent a
        # race (see below) — it's here so a request we already KNOW is a
        # repeat doesn't cost an extra outbound Paystack verify call.
        if Payment.objects(reference=reference).first():
            user = User.objects(id=request.user.id).first()
            return Response(
                {"user": user.to_public_dict(), "status": "already_verified"}
            )

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

        # Record the Payment BEFORE activating Pro — this ordering (ledger
        # entry first, side effect second) is what actually makes this
        # endpoint safe against a race, not the pre-check above. Two
        # concurrent requests for a brand-new reference (double-tap,
        # browser back+resubmit) can both sail past the pre-check before
        # either has written anything; record_payment()'s unique index is
        # the real lock. Whichever request loses this insert stops right
        # here instead of also calling activate_pro() — the winner
        # already has it covered — so a single charge can never activate
        # (and reset the paid period on) Pro more than once.
        if not record_payment(reference, user_id, interval, tx.get("amount", 0)):
            user = User.objects(id=request.user.id).first()
            return Response(
                {"user": user.to_public_dict(), "status": "already_verified"}
            )

        activate_pro(user_id, interval, tx)

        user = User.objects(id=request.user.id).first()
        return Response({"user": user.to_public_dict(), "status": "activated"})


class CancelSubscriptionView(APIView):
    """
    POST /api/v1/billing/cancel/ — marks the subscription as cancelled but
    does NOT downgrade the user immediately. The UI promises "You keep Pro
    until your billing ends", so `user.plan` and `user.plan_expires_at`
    are left untouched here; expire_subscriptions.py (run hourly) is what
    actually flips a cancelled-and-lapsed subscription over to Free once
    current_period_end has passed — and sends its own separate
    "your Pro access has ended" notification/email at that point.
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

        if event_id:
            # Idempotency — skip duplicates. The .first() check below is
            # only a fast-path optimization, NOT the actual guard: Paystack
            # can (and does) redeliver a webhook, and two near-simultaneous
            # deliveries of the same event can both see "not found" here
            # before either has saved. event_id's unique index is what
            # actually prevents a duplicate PaystackEvent row — so the
            # insert itself is wrapped in try/except: whichever delivery
            # loses that race just stops (200, no reprocessing) instead of
            # raising a 500 that would make Paystack retry the "duplicate"
            # unnecessarily.
            if PaystackEvent.objects(event_id=str(event_id)).first():
                return HttpResponse(status=200)
            try:
                PaystackEvent(
                    event_id=str(event_id), event_type=event_type, payload=payload
                ).save(force_insert=True)
            except NotUniqueError:
                return HttpResponse(status=200)
        else:
            # No event id to dedupe on — shouldn't happen for a real
            # Paystack delivery, but don't collide every id-less payload
            # onto the same empty-string unique key (which would silently
            # drop every one after the first) or crash on a malformed one.
            # Just log it and keep processing without an idempotency
            # record for this particular delivery.
            logger.warning("Paystack webhook payload missing an event id: %r", payload)

        data = payload.get("data", {})
        sub = Subscription.objects(
            paystack_subscription_code=data.get("subscription_code")
        ).first()
        user_id = sub.user_id if sub else None

        if event_type == "charge.success":
            metadata = data.get("metadata", {})
            uid = metadata.get("user_id") or user_id
            interval = metadata.get("interval", "monthly")
            charge_reference = data.get("reference", "")
            # Renewal charges (charge_renewals.py) already record their own
            # Payment row and activate Pro synchronously right after the
            # charge succeeds — skip here to avoid a duplicate, contradictory
            # "Welcome to Pro 🎉" notification on a renewal.
            if uid and not metadata.get("renewal"):
                if not charge_reference:
                    logger.warning(
                        "charge.success webhook missing data.reference — "
                        "skipping activation (can't safely dedupe without "
                        "one). payload=%r",
                        payload,
                    )
                # Record BEFORE activating — same ordering as
                # VerifyPaymentView, for the same reason: this webhook can
                # race (or simply duplicate-deliver, or arrive after) the
                # same charge already processed via /billing/verify/, and
                # record_payment()'s unique index — not a pre-check — is
                # what actually prevents activate_pro() from running twice
                # for one charge.
                elif record_payment(
                    charge_reference, uid, interval, data.get("amount", 0)
                ):
                    activate_pro(uid, interval, data)

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
                    body="We couldn't renew your Pro subscription please update your payment details.",
                ).save()

        return HttpResponse(status=200)
