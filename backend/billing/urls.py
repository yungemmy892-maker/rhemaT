from django.urls import path

from .views import (
    CancelSubscriptionView,
    InitiatePaymentView,
    PaystackWebhookView,
    PricingView,
    VerifyPaymentView,
)

urlpatterns = [
    path("pricing/", PricingView.as_view(), name="billing-pricing"),
    path("initiate/", InitiatePaymentView.as_view(), name="billing-initiate"),
    path("verify/", VerifyPaymentView.as_view(), name="billing-verify"),
    path("cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
    path("webhook/", PaystackWebhookView.as_view(), name="billing-webhook"),
]
