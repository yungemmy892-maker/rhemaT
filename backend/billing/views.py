import hashlib
import json
import logging
import time

from django.conf import settings
from django.http import HttpResponse
from mongoengine.errors import NotUniqueError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from users.models import User

from . import bachs
from .models import BachsEvent, Payment, PaystackEvent, Subscription
from .paystack import (
    initialize_transaction,
    verify_transaction,
    verify_webhook_signature,
)
from .serializers import (
    BachsInitiatePaymentSerializer,
    InitiatePaymentSerializer,
    VerifyPaymentSerializer,
)
from .services import activate_plan, record_payment, sync_bachs_subscription

logger = logging.getLogger(__name__)

NGN_PRICES = {
    "Pro": {
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
    },
    "Family": {
        "monthly": {
            "kobo": settings.FAMILY_PLAN_MONTHLY_KOBO,
            "label": "₦2,500/month",
            "naira": 2500,
        },
        "annual": {
            "kobo": settings.FAMILY_PLAN_ANNUAL_KOBO,
            "label": "₦22,500/year",
            "naira": 22500,
            "savings": "Save ₦7,500",
        },
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


BACHS_PRICES = {
    "NGN": {
        "symbol": "₦",
        "plans": {
            "Pro": {
                "monthly": {
                    "naira": settings.BACHS_NGN_PRO_MONTHLY_NAIRA,
                },
                "annual": {
                    "naira": settings.BACHS_NGN_PRO_ANNUAL_NAIRA,
                    "savings": "Save ₦3,000",
                },
            },
            "Family": {
                "monthly": {
                    "naira": settings.BACHS_NGN_FAMILY_MONTHLY_NAIRA,
                },
                "annual": {
                    "naira": settings.BACHS_NGN_FAMILY_ANNUAL_NAIRA,
                    "savings": "Save ₦7,500",
                },
            },
        },
    },
    "USD": {
        "symbol": "$",
        "plans": {
            "Pro": {
                "monthly": {"dollars": settings.BACHS_USD_PRO_MONTHLY_CENTS / 100},
                "annual": {
                    "dollars": settings.BACHS_USD_PRO_ANNUAL_CENTS / 100,
                    "savings": "Save $15",
                },
            },
            "Family": {
                "monthly": {"dollars": settings.BACHS_USD_FAMILY_MONTHLY_CENTS / 100},
                "annual": {
                    "dollars": settings.BACHS_USD_FAMILY_ANNUAL_CENTS / 100,
                    "savings": "Save $36",
                },
            },
        },
    },
}

# One Bachs product per currency+plan+interval — see config/settings.py
# for why a product can't just take currency/interval as checkout params.
BACHS_PRODUCTS = {
    ("NGN", "Pro", "monthly"): settings.BACHS_NGN_PRO_MONTHLY_PRODUCT_ID,
    ("NGN", "Pro", "annual"): settings.BACHS_NGN_PRO_ANNUAL_PRODUCT_ID,
    ("NGN", "Family", "monthly"): settings.BACHS_NGN_FAMILY_MONTHLY_PRODUCT_ID,
    ("NGN", "Family", "annual"): settings.BACHS_NGN_FAMILY_ANNUAL_PRODUCT_ID,
    ("USD", "Pro", "monthly"): settings.BACHS_USD_PRO_MONTHLY_PRODUCT_ID,
    ("USD", "Pro", "annual"): settings.BACHS_USD_PRO_ANNUAL_PRODUCT_ID,
    ("USD", "Family", "monthly"): settings.BACHS_USD_FAMILY_MONTHLY_PRODUCT_ID,
    ("USD", "Family", "annual"): settings.BACHS_USD_FAMILY_ANNUAL_PRODUCT_ID,
}


class BachsPricingView(APIView):
    """GET /api/v1/billing/bachs/pricing/ — both NGN and USD plan prices
    (public). Bachs is now the sole gateway for new subscriptions in
    either currency; see config/settings.py's BACHS_* block for why
    Paystack's own pricing/checkout views below are left running
    unchanged rather than removed."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "currencies": BACHS_PRICES,
                "freeLimit": User.FREE_DAILY_SEARCH_LIMIT,
            }
        )


class InitiatePaymentView(APIView):
    """
    POST /api/v1/billing/initiate/
    Body: { "plan": "Pro"|"Family", "interval": "monthly"|"annual", "callback_url": "..." }

    Paystack checkout — kept fully functional but no longer linked from
    the frontend's Subscribe flow (new subscriptions go through Bachs on
    both currencies now, see BachsInitiatePaymentView). Left running so
    anyone who needs a manual/support-driven Paystack charge still can;
    charge_renewals.py/expire_subscriptions.py/the Paystack webhook all
    still depend on this gateway's Subscription rows continuing to work
    for existing subscribers regardless.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = data["plan"]
        interval = data["interval"]
        price = NGN_PRICES[plan][interval]

        try:
            tx = initialize_transaction(
                email=request.user.email,
                amount_kobo=price["kobo"],
                metadata={
                    "user_id": str(request.user.id),
                    "plan": plan,
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
                "plan": plan,
                "interval": interval,
            }
        )


class BachsInitiatePaymentView(APIView):
    """
    POST /api/v1/billing/bachs/initiate/
    Body: { "plan": "Pro"|"Family", "interval": "monthly"|"annual", "currency": "NGN"|"USD", "success_url": "...", "cancel_url": "..." }

    The sole checkout path for NEW subscriptions, either currency. Returns
    { "checkout_url": "..." } the frontend redirects to. Unlike Paystack,
    there's no separate verify-by-reference step: completing this checkout
    is what creates the Subscription on Bachs's side, and entitlement is
    granted asynchronously by BachsWebhookView on
    customer.subscription.created — the frontend just refreshes user state
    after landing back on success_url.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BachsInitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = data["plan"]
        interval = data["interval"]
        currency = data["currency"]
        product_id = BACHS_PRODUCTS.get((currency, plan, interval))

        if not product_id:
            logger.error(
                "No Bachs product configured for currency=%s plan=%s interval=%s — "
                "check BACHS_%s_%s_%s_PRODUCT_ID in settings.",
                currency,
                plan,
                interval,
                currency,
                plan.upper(),
                interval.upper(),
            )
            return Response(
                {
                    "error": {
                        "code": 500,
                        "message": f"This plan isn't available in {currency} right now.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Reuse an existing Bachs customer if this user has one (e.g. from
        # a previous subscription, even a since-cancelled one), rather
        # than creating a duplicate customer record on Bachs every time
        # they check out.
        existing_sub = Subscription.objects(user_id=str(request.user.id)).first()
        customer_id = (
            existing_sub.bachs_customer_id
            if existing_sub and existing_sub.bachs_customer_id
            else None
        )

        # Bucketed to the wall-clock minute so a genuine double-tap on
        # Subscribe reuses the same Bachs checkout instead of creating
        # two, while a real new attempt a few minutes later (e.g. the
        # first session expired) still gets a fresh one.
        idempotency_key = hashlib.sha256(
            f"{request.user.id}:{currency}:{plan}:{interval}:{int(time.time() // 60)}".encode()
        ).hexdigest()

        try:
            session = bachs.create_checkout_session(
                email=request.user.email,
                name=request.user.name or request.user.email.split("@")[0],
                product_id=product_id,
                metadata={
                    "user_id": str(request.user.id),
                    "plan": plan,
                    "interval": interval,
                    "currency": currency,
                },
                success_url=data["success_url"],
                cancel_url=data["cancel_url"],
                customer_id=customer_id,
                idempotency_key=idempotency_key,
            )
        except bachs.BachsError as exc:
            logger.error("Bachs initiate error: %s", exc)
            return Response(
                {
                    "error": {
                        "code": 502,
                        "message": "Payment gateway error. Please try again.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        price = BACHS_PRICES[currency]["plans"][plan][interval]
        return Response(
            {
                "checkout_url": bachs.checkout_url(session),
                "session_id": session.get("checkout_id", ""),
                "amount": price.get("naira") if currency == "NGN" else price.get("dollars"),
                "currency": currency,
                "plan": plan,
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
        plan = metadata.get("plan", "Pro")
        interval = metadata.get("interval", "monthly")
        user_id = metadata.get("user_id", str(request.user.id))

        # Record the Payment BEFORE activating — this ordering (ledger
        # entry first, side effect second) is what actually makes this
        # endpoint safe against a race, not the pre-check above. Two
        # concurrent requests for a brand-new reference (double-tap,
        # browser back+resubmit) can both sail past the pre-check before
        # either has written anything; record_payment()'s unique index is
        # the real lock. Whichever request loses this insert stops right
        # here instead of also calling activate_plan() — the winner
        # already has it covered — so a single charge can never activate
        # (and reset the paid period on) a plan more than once.
        if not record_payment(
            reference,
            user_id,
            plan,
            interval,
            gateway="paystack",
            amount_kobo=tx.get("amount", 0),
        ):
            user = User.objects(id=request.user.id).first()
            return Response(
                {"user": user.to_public_dict(), "status": "already_verified"}
            )

        activate_plan(user_id, plan, interval, tx)

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

    Gateway-dependent for the actual cancellation itself: Paystack never
    owns recurring billing here (charge_renewals.py does — see
    Subscription's renewal_attempts comment), so there's nothing on
    Paystack's side to cancel; flipping the local status is what actually
    stops future renewal attempts. Bachs is the opposite — it renews the
    subscription itself, so a local-only status flip would do nothing to
    stop the next charge. Bachs's own API call has to be the one that
    actually cancels it.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        sub = Subscription.objects(user_id=str(user.id)).first()
        plan_name = sub.plan if sub else "Pro"

        if sub and sub.gateway == "bachs" and sub.bachs_subscription_id:
            try:
                bachs.cancel_subscription(sub.bachs_subscription_id, at_period_end=True)
            except bachs.BachsError as exc:
                logger.error(
                    "Bachs cancel_subscription failed for user_id=%s "
                    "subscription_id=%s: %s",
                    user.id,
                    sub.bachs_subscription_id,
                    exc,
                )
                return Response(
                    {
                        "error": {
                            "code": 502,
                            "message": "Could not cancel with the payment gateway. Please try again.",
                        }
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            # Bachs will also send customer.subscription.updated with
            # cancel_at_period_end=true — this local flip happens anyway
            # (rather than waiting for that webhook) so the UI reflects
            # "cancelled" immediately instead of however long delivery
            # takes.

        Subscription.objects(user_id=str(user.id)).update(set__status="cancelled")
        Notification(
            user_id=str(user.id),
            kind="pro_upsell",
            title=f"{plan_name} subscription cancelled",
            body=f"Your {plan_name} features will remain until the end of the billing period.",
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
            plan = metadata.get("plan", "Pro")
            interval = metadata.get("interval", "monthly")
            charge_reference = data.get("reference", "")
            # Renewal charges (charge_renewals.py) already record their own
            # Payment row and activate the plan synchronously right after the
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
                # what actually prevents activate_plan() from running twice
                # for one charge.
                elif record_payment(
                    charge_reference,
                    uid,
                    plan,
                    interval,
                    gateway="paystack",
                    amount_kobo=data.get("amount", 0),
                ):
                    activate_plan(uid, plan, interval, data)

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


class BachsWebhookView(APIView):
    """
    POST /api/v1/billing/bachs/webhook/
    Bachs sends signed POST events here — this is the ONLY thing that
    grants or revokes USD/Bachs plan access; there's no client-side verify
    endpoint the way Paystack has one. Set this URL in the Bachs Dashboard
    webhook settings.

    Handles subscription state as a full sync, not deltas — every
    customer.subscription.* event just overwrites the local Subscription
    mirror from whatever Bachs sent, rather than trying to interpret what
    specifically changed (see sync_bachs_subscription's docstring).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Bachs-Signature", "")
        timestamp = request.headers.get("X-Bachs-Timestamp", "")
        if not bachs.verify_webhook_signature(request.body, signature, timestamp):
            return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_id = payload.get("id", "")
        event_type = payload.get("type", "")
        data = payload.get("data", {})

        if event_id:
            # Same idempotency pattern as PaystackEvent above — the insert
            # itself (not this .first() pre-check) is what actually
            # prevents double-processing a redelivered event. Bachs
            # guarantees at-least-once delivery, so the same event can and
            # will arrive more than once.
            if BachsEvent.objects(event_id=str(event_id)).first():
                return HttpResponse(status=200)
            try:
                BachsEvent(
                    event_id=str(event_id), event_type=event_type, payload=payload
                ).save(force_insert=True)
            except NotUniqueError:
                return HttpResponse(status=200)
        else:
            logger.warning("Bachs webhook payload missing an event id: %r", payload)

        metadata = data.get("metadata", {}) or {}

        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            plan = metadata.get("plan") or (data.get("product", {}) or {}).get(
                "metadata", {}
            ).get("plan")
            user_id = metadata.get("user_id")
            if not user_id:
                # customer.subscription.updated deliveries after the first
                # one don't necessarily carry the checkout session's
                # metadata — fall back to looking the subscription up by
                # its own Bachs ID, the same way the Paystack handler
                # falls back to a stored subscription_code.
                existing = Subscription.objects(
                    bachs_subscription_id=data.get("id")
                ).first()
                user_id = existing.user_id if existing else None
                plan = plan or (existing.plan if existing else None)
            if user_id and plan:
                sync_bachs_subscription(user_id, plan, data)
            else:
                logger.warning(
                    "Bachs %s event missing enough info to sync (user_id=%r plan=%r): %r",
                    event_type,
                    user_id,
                    plan,
                    payload,
                )

        elif event_type == "customer.subscription.deleted":
            sub = Subscription.objects(bachs_subscription_id=data.get("id")).first()
            if sub:
                sub.status = "cancelled"
                sub.save()
                # Deliberately NOT downgrading user.plan here — same
                # reasoning as CancelSubscriptionView: access should last
                # until current_period_end, and expire_subscriptions.py
                # (gateway-agnostic) is what handles that once it's due.

        elif event_type == "collection.succeeded":
            # Renewal (or initial) charge landed — record it in the ledger.
            # Entitlement itself (user.plan / plan_expires_at) is driven by
            # the subscription events above, not here, so this can't race
            # activation: a collection.succeeded that arrives before the
            # matching customer.subscription.created just records payment
            # a little early, it doesn't grant access on its own.
            user_id = metadata.get("user_id")
            plan = metadata.get("plan")
            interval = metadata.get("interval", "monthly")
            charge_id = data.get("id", "")
            if user_id and plan and charge_id:
                record_payment(
                    charge_id,
                    user_id,
                    plan,
                    interval,
                    gateway="bachs",
                    amount_usd_cents=_dollars_to_cents_local(data.get("amount")),
                )

        elif event_type == "collection.failed":
            sub = Subscription.objects(
                bachs_subscription_id=(data.get("subscription", {}) or {}).get("id")
            ).first()
            if sub:
                Notification(
                    user_id=sub.user_id,
                    kind="pro_upsell",
                    title="Payment failed",
                    body=f"We couldn't renew your {sub.plan} subscription — please update your payment details.",
                ).save()

        return HttpResponse(status=200)


def _dollars_to_cents_local(amount) -> int | None:
    """Same conversion as services._dollars_to_cents — duplicated locally
    rather than imported since it's a one-line private helper and importing
    a leading-underscore name across modules is a bigger smell than a
    three-line duplicate."""
    if amount is None:
        return None
    try:
        return round(float(amount) * 100)
    except (ValueError, TypeError):
        logger.error("Could not parse Bachs collection amount %r", amount)
        return None