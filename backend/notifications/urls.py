from django.urls import path

from .views import (
    MarkAllReadView,
    NotificationListView,
    PushSubscribeView,
    PushUnsubscribeView,
    VapidPublicKeyView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path("mark-all-read/", MarkAllReadView.as_view(), name="notifications-mark-all-read"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="notifications-push-subscribe"),
    path("push/unsubscribe/", PushUnsubscribeView.as_view(), name="notifications-push-unsubscribe"),
    path("push/vapid-public-key/", VapidPublicKeyView.as_view(), name="notifications-vapid-key"),
]
