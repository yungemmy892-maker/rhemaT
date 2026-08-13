from django.urls import path

from .views import (
    DeleteNotificationView,
    MarkAllReadView,
    NotificationListView,
    PushSubscribeView,
    PushUnsubscribeView,
    VapidPublicKeyView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path(
        "mark-all-read/", MarkAllReadView.as_view(), name="notifications-mark-all-read"
    ),
    path(
        "push/subscribe/",
        PushSubscribeView.as_view(),
        name="notifications-push-subscribe",
    ),
    path(
        "push/unsubscribe/",
        PushUnsubscribeView.as_view(),
        name="notifications-push-unsubscribe",
    ),
    path(
        "push/vapid-public-key/",
        VapidPublicKeyView.as_view(),
        name="notifications-vapid-key",
    ),
    # Must stay LAST — a single-segment dynamic pattern like this one would
    # otherwise swallow "mark-all-read/" and "push/..." themselves (Django
    # matches the first pattern whose shape fits, and "mark-all-read" is
    # itself a valid single path segment).
    path(
        "<str:notification_id>/",
        DeleteNotificationView.as_view(),
        name="notifications-delete",
    ),
]