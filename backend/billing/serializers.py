from urllib.parse import urlparse

from django.conf import settings
from rest_framework import serializers


class InitiatePaymentSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["Pro", "Family"], default="Pro")
    interval = serializers.ChoiceField(choices=["monthly", "annual"])
    callback_url = serializers.URLField(
        required=False,
        default=None,
        help_text="Frontend URL Paystack redirects to after payment.",
    )

    def validate_callback_url(self, value):
        if value is None:
            return None
        # M4: without this, a client-supplied callback_url is forwarded to
        # Paystack unvalidated and used as a post-payment browser redirect —
        # an open-redirect / phishing vector class. Confine it to our own
        # frontend origin.
        allowed_prefix = settings.FRONTEND_URL.rstrip("/")
        if not value.startswith(allowed_prefix):
            raise serializers.ValidationError(
                "callback_url must point to the VerseID app."
            )
        return value

    def validate(self, attrs):
        # Derive the default from settings rather than a hardcoded literal,
        # so it always passes the allowlist check above regardless of which
        # environment (dev/prod) this is running in.
        if not attrs.get("callback_url"):
            attrs["callback_url"] = (
                f"{settings.FRONTEND_URL.rstrip('/')}/app/subscription?status=success"
            )
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()


class BachsInitiatePaymentSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["Pro", "Family"], default="Pro")
    interval = serializers.ChoiceField(choices=["monthly", "annual"])
    currency = serializers.ChoiceField(choices=["NGN", "USD"], default="USD")
    success_url = serializers.URLField(required=False, default=None)
    cancel_url = serializers.URLField(required=False, default=None)

    def _validate_own_origin(self, value, field_name):
        if value is None:
            return None
        # Same open-redirect concern as InitiatePaymentSerializer's
        # callback_url above — a client-supplied redirect target forwarded
        # to Bachs unvalidated is a phishing vector. Confine both to our
        # own frontend origin.
        #
        # Deliberately comparing scheme+hostname via urlparse rather than
        # a raw string prefix: verseid.top and www.verseid.top are the
        # same site to any visitor and to Vercel's own domain config, but
        # "https://www.verseid.top/...".startswith("https://verseid.top")
        # is False — a bare string-prefix check rejects a perfectly
        # legitimate request just because of that one subdomain. Port is
        # deliberately ignored too (matters for local dev against
        # different dev-server ports); what actually matters for the
        # open-redirect concern this exists for is that the hostname
        # can't be swapped for an attacker-controlled domain, which this
        # still catches.
        target = urlparse(value)
        allowed = urlparse(settings.FRONTEND_URL)

        def bare_host(host: str | None) -> str:
            host = (host or "").lower()
            return host[4:] if host.startswith("www.") else host

        if target.scheme != allowed.scheme or bare_host(target.hostname) != bare_host(
            allowed.hostname
        ):
            raise serializers.ValidationError(f"{field_name} must point to the VerseID app.")
        return value

    def validate_success_url(self, value):
        return self._validate_own_origin(value, "success_url")

    def validate_cancel_url(self, value):
        return self._validate_own_origin(value, "cancel_url")

    def validate(self, attrs):
        base = settings.FRONTEND_URL.rstrip("/")
        if not attrs.get("success_url"):
            attrs["success_url"] = f"{base}/app/subscription?status=success&gateway=bachs"
        if not attrs.get("cancel_url"):
            attrs["cancel_url"] = f"{base}/app/subscription?status=cancelled&gateway=bachs"
        return attrs