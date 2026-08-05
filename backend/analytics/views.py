import datetime
import hmac
from collections import Counter

from django.conf import settings
from mongoengine.errors import ValidationError as MongoValidationError
from mongoengine.queryset.visitor import Q
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.models import resolve_verse
from billing.models import Subscription
from preferences.models import SavedVerse, UserSettings
from search.models import SearchHistory
from users.models import PasswordResetToken, RefreshToken, User


class HasAdminKey(BasePermission):
    message = "Invalid or missing admin API key."

    def has_permission(self, request, view):
        key = getattr(settings, "ADMIN_API_KEY", "")
        return bool(key) and hmac.compare_digest(
            request.headers.get("X-Admin-Key") or "", key
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


def _serialize_user(u: User) -> dict:
    """Shared shape for a user in API responses — AdminStatsView's
    recentUsers and AdminUserSearchView's results both use this, so the
    frontend's shared table renderer can treat both identically. `id` is
    required by the frontend's delete button to know which user to
    target — it was missing from recentUsers before this endpoint pair
    was added, since nothing previously needed to reference a specific
    user by id."""
    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "createdAt": u.created_at.isoformat(),
        "plan": u.plan,
        "signupMethod": "google" if u.google_id else "email",
        "identifiedCount": u.identified_count,
    }


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
        google_signups = User.objects(
            google_id__exists=True, google_id__ne=None
        ).count()

        pro_users = User.objects(plan="Pro").count()

        active_subs = list(Subscription.objects(status="active"))
        mrr_kobo = sum(
            (
                (sub.amount_kobo or 0)
                if sub.interval == "monthly"
                else (sub.amount_kobo or 0) / 12
            )
            for sub in active_subs
        )

        # Top 10 most-identified verses (matched searches only).
        verse_counter: Counter = Counter()
        for row in SearchHistory.objects(matched=True, verse_id__ne=None).only(
            "verse_id"
        ):
            verse_counter[row.verse_id] += 1
        top_verses = []
        for verse_id, count in verse_counter.most_common(10):
            verse = resolve_verse(verse_id)
            top_verses.append(
                {
                    "verseId": verse_id,
                    "ref": verse.ref if verse else verse_id,
                    "count": count,
                }
            )

        recent_users = [
            _serialize_user(u) for u in User.objects.order_by("-created_at").limit(20)
        ]

        return Response(
            {
                "generatedAt": now.isoformat(),
                "totals": {
                    "users": total_users,
                    "newToday": User.objects(created_at__gte=today_start).count(),
                    "newThisWeek": User.objects(created_at__gte=week_ago).count(),
                    "newThisMonth": User.objects(created_at__gte=month_ago).count(),
                    "activeLast7Days": User.objects(
                        last_login_at__gte=week_ago
                    ).count(),
                    "googleSignups": google_signups,
                    "emailSignups": total_users - google_signups,
                    "proUsers": pro_users,
                    "freeUsers": total_users - pro_users,
                    "totalSearches": SearchHistory.objects.count(),
                    "searchesToday": SearchHistory.objects(
                        created_at__gte=today_start
                    ).count(),
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


class AdminUserSearchView(APIView):
    authentication_classes = []
    permission_classes = [HasAdminKey]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        # Mirrors the frontend's own 2-character minimum — enforced here
        # too since this endpoint could be hit directly, not just via
        # the dashboard's debounced search box.
        if len(query) < 2:
            return Response({"users": []})

        matches = (
            User.objects(Q(name__icontains=query) | Q(email__icontains=query))
            .order_by("-created_at")
            .limit(50)
        )

        return Response({"users": [_serialize_user(u) for u in matches]})


class AdminUserDeleteView(APIView):
    authentication_classes = []
    permission_classes = [HasAdminKey]

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, MongoValidationError):
            return Response(status=404)

        active_sub = Subscription.objects(user_id=user_id, status="active").first()
        if active_sub:
            return Response(
                {
                    "detail": (
                        "This user has an active subscription. Cancel it in "
                        "Paystack (or let it lapse) before deleting the "
                        "account — otherwise their card keeps being charged "
                        "for a subscription tied to a user that no longer "
                        "exists."
                    )
                },
                status=409,
            )

        # No transaction here — this project isn't set up with MongoDB
        # replica-set sessions for multi-document transactions, so this
        # cleanup isn't atomic. Deleting the User document LAST is
        # deliberate: if anything below raises partway through, the user
        # still exists and nothing irreversible has happened, rather than
        # ending up with a deleted account whose cleanup silently half-ran.
        SearchHistory.objects(user_id=user_id).delete()
        SavedVerse.objects(user_id=user_id).delete()
        UserSettings.objects(user_id=user_id).delete()
        RefreshToken.objects(user_id=user_id).delete()
        PasswordResetToken.objects(user_id=user_id).delete()
        # Any Subscription here is guaranteed non-active (active already
        # returned above) — safe to remove, since unlike Payment this is
        # current-state tracking, not a ledger.
        Subscription.objects(user_id=user_id).delete()
        # Payment is deliberately left untouched: its own docstring calls
        # it a "permanent, append-only record" — a financial/audit ledger
        # that should outlive the account it was charged against, the same
        # way most billing systems retain transaction history after
        # account deletion for accounting and dispute purposes.

        user.delete()
        return Response(status=204)
