from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from .models import Notification, PushSubscription
from .serializers import PushSubscriptionSerializer


class VapidPublicKeyView(APIView):
    """GET /api/v1/notifications/push/vapid-public-key/ — needed by the
    browser's PushManager.subscribe({ applicationServerKey }) call."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"publicKey": settings.VAPID_PUBLIC_KEY})


class NotificationListView(APIView):
    """GET /api/v1/notifications/ — feed for the Notifications screen."""

    def get(self, request):
        items = Notification.objects(user_id=str(request.user.id)).limit(50)
        return Response([n.to_dict() for n in items])


class MarkAllReadView(APIView):
    """POST /api/v1/notifications/mark-all-read/"""

    def post(self, request):
        Notification.objects(user_id=str(request.user.id), read=False).update(set__read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushSubscribeView(APIView):
    """
    POST /api/v1/notifications/push/subscribe/
    Body: the PushSubscription object from the browser's
    `registration.pushManager.subscribe()` call:
    { "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } }
    """

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id = str(request.user.id)

        existing = PushSubscription.objects(endpoint=data["endpoint"]).first()
        if existing:
            existing.user_id = user_id
            existing.p256dh = data["keys"]["p256dh"]
            existing.auth = data["keys"]["auth"]
            existing.save()
        else:
            PushSubscription(
                user_id=user_id,
                endpoint=data["endpoint"],
                p256dh=data["keys"]["p256dh"],
                auth=data["keys"]["auth"],
            ).save()

        return Response(status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    """POST /api/v1/notifications/push/unsubscribe/ — { "endpoint": "..." }"""

    def post(self, request):
        endpoint = request.data.get("endpoint")
        if endpoint:
            PushSubscription.objects(user_id=str(request.user.id), endpoint=endpoint).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
