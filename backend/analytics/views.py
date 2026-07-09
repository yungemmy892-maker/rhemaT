import datetime
from collections import Counter

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.models import resolve_verse
from billing.models import Subscription
from preferences.models import SavedVerse
from search.models import SearchHistory
from users.models import User


class HasAdminKey(BasePermission):
    message = "Invalid or missing admin API key."

    def has_permission(self, request, view):
        key = getattr(settings, "ADMIN_API_KEY", "")
        return (
            bool(key)
            and request.headers.get("X-Admin-Key") == key
        )

def _day_start(d: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(d, datetime.time.min)


def _daily_counts(document_cls, days: int) -> list[dict]:
    """Per-day document counts for the last `days` days (oldest first)."""
    today = datetime.datetime.utcnow().date()
    out = []
    for i in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=i)
        start = _day_start(day)
        end = start + datetime.timedelta(days=1)
        count = document_cls.objects(created_at__gte=start, created_at__lt=end).count()
        out.append({"date": day.isoformat(), "count": count})
    return out


class AdminStatsView(APIView):
    # The global DEFAULT_AUTHENTICATION_CLASSES (JWTAuthentication) runs
    # before permission_classes on every APIView by default — without this
    # override, a request with no "Authorization: Bearer ..." header gets
    # rejected with 401 by the JWT authenticator itself, before HasAdminKey
    # (which checks X-Admin-Key instead) ever runs. This view intentionally
    # uses a completely different auth scheme, so it opts out of JWT auth
    # entirely.
    authentication_classes = []
    permission_classes = [HasAdminKey]

    def get(self, request):
        now = datetime.datetime.utcnow()
        today_start = _day_start(now.date())
        week_ago = now - datetime.timedelta(days=7)
        month_ago = now - datetime.timedelta(days=30)

        total_users = User.objects.count()
        google_signups = User.objects(google_id__exists=True, google_id__ne=None).count()

        pro_users = User.objects(plan="Pro").count()

        active_subs = list(Subscription.objects(status="active"))
        mrr_kobo = sum(
            (sub.amount_kobo or 0) if sub.interval == "monthly" else (sub.amount_kobo or 0) / 12
            for sub in active_subs
        )

        # Top 10 most-identified verses (matched searches only).
        verse_counter: Counter = Counter()
        for row in SearchHistory.objects(matched=True, verse_id__ne=None).only("verse_id"):
            verse_counter[row.verse_id] += 1
        top_verses = []
        for verse_id, count in verse_counter.most_common(10):
            verse = resolve_verse(verse_id)
            top_verses.append({"verseId": verse_id, "ref": verse.ref if verse else verse_id, "count": count})

        recent_users = [
            {
                "name": u.name,
                "email": u.email,
                "createdAt": u.created_at.isoformat(),
                "plan": u.plan,
                "signupMethod": "google" if u.google_id else "email",
                "identifiedCount": u.identified_count,
            }
            for u in User.objects.order_by("-created_at").limit(20)
        ]

        return Response(
            {
                "generatedAt": now.isoformat(),
                "totals": {
                    "users": total_users,
                    "newToday": User.objects(created_at__gte=today_start).count(),
                    "newThisWeek": User.objects(created_at__gte=week_ago).count(),
                    "newThisMonth": User.objects(created_at__gte=month_ago).count(),
                    "activeLast7Days": User.objects(last_login_at__gte=week_ago).count(),
                    "googleSignups": google_signups,
                    "emailSignups": total_users - google_signups,
                    "proUsers": pro_users,
                    "freeUsers": total_users - pro_users,
                    "totalSearches": SearchHistory.objects.count(),
                    "searchesToday": SearchHistory.objects(created_at__gte=today_start).count(),
                    "totalSaved": SavedVerse.objects.count(),
                    "activeSubscriptions": len(active_subs),
                    "mrrNaira": round(mrr_kobo / 100, 2),
                },
                "signupsByDay": _daily_counts(User, 30),
                "searchesByDay": _daily_counts(SearchHistory, 30),
                "topVerses": top_verses,
                "recentUsers": recent_users,
            }
        )