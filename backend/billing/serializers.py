from rest_framework import serializers


class InitiatePaymentSerializer(serializers.Serializer):
    interval = serializers.ChoiceField(choices=["monthly", "annual"])
    callback_url = serializers.URLField(
        required=False,
        default="http://localhost:5173/app/subscription?status=success",
        help_text="Frontend URL Paystack redirects to after payment.",
    )


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()
