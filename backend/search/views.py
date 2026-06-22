import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.models import resolve_verse
from notifications.models import Notification
from users.models import User

from .matching import find_best_match
from .models import SearchHistory
from .serializers import IdentifySerializer

# Streak lengths worth celebrating with a notification — avoids spamming a
# notification every single day, matching the spirit of the original mock
# ("Reading streak: 12 days") which only showed up occasionally.
STREAK_MILESTONES = (3, 7, 14, 30, 60, 100, 365)


class IdentifyView(APIView):
    """
    POST /api/v1/search/identify/
    Body: { "query": "for god so loved the world", "version": "KJV" }
    ("version" is optional — omit it to search both KJV and WEB and let the
    higher-confidence match win.)

    Used by both the Voice screen (after Web Speech API transcription) and
    the Text search screen — same matching pipeline either way, since by
    the time it reaches the backend a voice transcript is just text.
    """

    def post(self, request):
        serializer = IdentifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        version = serializer.validated_data.get("version")

        user = request.user
        if not user.has_search_quota():
            return Response(
                {
                    "error": {
                        "code": 429,
                        "message": (
                            f"You've used all {user.FREE_DAILY_SEARCH_LIMIT} free searches for today. "
                            "Upgrade to Pro for unlimited searches."
                        ),
                    },
                    "dailySearchesRemaining": 0,
                    "dailySearchLimit": user.FREE_DAILY_SEARCH_LIMIT,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # The search itself is the metered action (matching the existing
        # "Free plan includes 20 searches per day" copy on the Subscription
        # screen) — counts regardless of whether a match is found.
        user.record_search()
        user.save()

        result = find_best_match(query, version=version)

        SearchHistory(
            user_id=str(request.user.id),
            query=query,
            verse_id=result["verse"]["id"] if result else None,
            version=result["verse"]["version"] if result else (version or "KJV"),
            matched=bool(result),
            confidence=result["confidence"] if result else 0.0,
        ).save()

        if result:
            User.objects(id=request.user.id).update(
                inc__identified_count=1,
            )
            user = User.objects(id=request.user.id).first()
            previous_streak = user.streak_count
            user.touch_streak()
            user.save()

            if user.streak_count != previous_streak and user.streak_count in STREAK_MILESTONES:
                Notification(
                    user_id=str(user.id),
                    kind="streak",
                    title=f"Reading streak: {user.streak_count} days",
                    body="You're on fire — keep the momentum going.",
                ).save()

        remaining = user.daily_searches_remaining()

        if not result:
            return Response(
                {"matched": False, "query": query, "dailySearchesRemaining": remaining},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"matched": True, "query": query, "dailySearchesRemaining": remaining, **result},
            status=status.HTTP_200_OK,
        )


class RecentSearchesView(APIView):
    """GET /api/v1/search/recent/ — last 10 searches for Home + Library."""

    def get(self, request):
        items = (
            SearchHistory.objects(user_id=str(request.user.id))
            .order_by("-created_at")
            .limit(10)
        )
        results = []
        for item in items:
            data = item.to_dict()
            verse = resolve_verse(item.verse_id, item.version) if item.verse_id else None
            data["verse"] = verse.to_dict() if verse else None
            results.append(data)
        return Response(results)
