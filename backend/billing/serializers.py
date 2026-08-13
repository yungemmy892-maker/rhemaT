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