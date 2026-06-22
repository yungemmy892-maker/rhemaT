import datetime
import json
import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from users.models import User

from .models import PaystackEvent, Subscription
from .paystack import (
    PaystackError,
    initialize_transaction,
    verify_transaction,
    verify_webhook_signature,
)
from .serializers import InitiatePaymentSerializer, VerifyPaymentSerializer

logger = logging.getLogger(__name__)

NGN_PRICES = {
    "monthly": {
        "kobo": settings.PLAN_MONTHLY_KOBO,
        "label": "₦2,500/month",
        "naira": 2500,
    },
    "annual": {
        "kobo": settings.PLAN_ANNUAL_KOBO,
        "label": "₦20,000/year",
        "naira": 20000,
        "savings": "Save ₦10,000",
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
                    "cancel_action": data["callback_url"].replace("status=success", "status=cancelled"),
                },
                callback_url=data["callback_url"],
            )
        except Exception as exc:
            logger.error("Paystack initiate error: %s", exc)
            return Response(
                {"error": {"code": 502, "message": "Payment gateway error. Please try again."}},
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

        try:
            tx = verify_transaction(reference)
        except Exception as exc:
            logger.error("Paystack verify error: %s", exc)
            return Response(
                {"error": {"code": 502, "message": "Could not verify payment. Please contact support."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if tx["status"] != "success":
            return Response(
                {"error": {"code": 402, "message": f"Payment not completed (status: {tx['status']})."}},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        metadata = tx.get("metadata", {})
        interval = metadata.get("interval", "monthly")
        user_id = metadata.get("user_id", str(request.user.id))

        _activate_pro(user_id, interval, tx)
        user = User.objects(id=request.user.id).first()
        return Response({"user": user.to_public_dict(), "status": "activated"})


class CancelSubscriptionView(APIView):
    """POST /api/v1/billing/cancel/ — immediately downgrades to Free."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        Subscription.objects(user_id=str(user.id)).update(set__status="cancelled")
        user.plan = "Free"
        user.plan_expires_at = None
        user.save()
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

        PaystackEvent(event_id=str(event_id), event_type=event_type, payload=payload).save()

        data = payload.get("data", {})
        customer_code = data.get("customer", {}).get("customer_code")
        sub = Subscription.objects(paystack_subscription_code=data.get("subscription_code")).first()
        user_id = sub.user_id if sub else None

        if event_type == "charge.success":
            metadata = data.get("metadata", {})
            uid = metadata.get("user_id") or user_id
            interval = metadata.get("interval", "monthly")
            if uid:
                _activate_pro(uid, interval, data)

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


def _activate_pro(user_id: str, interval: str, tx_data: dict):
    """Shared helper: marks user as Pro and upserts the Subscription record."""
    user = User.objects(id=user_id).first()
    if user is None:
        return

    days = 30 if interval == "monthly" else 365
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)

    user.plan = "Pro"
    user.plan_expires_at = expires_at
    user.save()

    Subscription.objects(user_id=user_id).upsert_one(
        set__paystack_customer_code=tx_data.get("customer", {}).get("customer_code", ""),
        set__paystack_subscription_code=tx_data.get("subscription_code", ""),
        set__paystack_authorization_code=tx_data.get("authorization", {}).get("authorization_code", ""),
        set__interval=interval,
        set__amount_kobo=tx_data.get("amount", 0),
        set__status="active",
        set__current_period_end=expires_at,
        set__updated_at=datetime.datetime.utcnow(),
    )

    Notification(
        user_id=user_id,
        kind="pro_upsell",
        title="Welcome to VerseID Pro 🎉",
        body="Unlimited searches and all premium features are now unlocked.",
    ).save()
