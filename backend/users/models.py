import datetime
import uuid

import mongoengine as me
from django.conf import settings


def _gen_id():
    return uuid.uuid4().hex


def _resolve_avatar_url(avatar: str | None) -> str | None:
    """
    `avatar` is either a full external URL (Google profile photo, DiceBear
    fallback) or a path relative to MEDIA_ROOT (an uploaded avatar, e.g.
    "avatars/<id>.jpg"). Uploaded paths are resolved to an absolute URL
    using BACKEND_BASE_URL so the frontend can render it regardless of
    which origin it's served from.
    """
    if not avatar:
        return avatar
    if avatar.startswith("http://") or avatar.startswith("https://"):
        return avatar
    return f"{settings.BACKEND_BASE_URL}{settings.MEDIA_URL}{avatar}"


class User(me.Document):
    """
    A VerseID account. Created on first Google sign-in OR on email/password
    registration. `google_id` and `password_hash` are both optional since a
    user may have only ever used one method — but at least one should be
    set for any real account.
    """

    id = me.StringField(primary_key=True, default=_gen_id)
    google_id = me.StringField(unique=True, sparse=True)
    password_hash = me.StringField()
    email = me.EmailField(required=True, unique=True)
    name = me.StringField(required=True)
    avatar = me.StringField()
    plan = me.StringField(choices=("Free", "Pro"), default="Free")
    plan_expires_at = me.DateTimeField(null=True)

    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    last_login_at = me.DateTimeField(default=datetime.datetime.utcnow)

    # Lightweight stats shown on the Profile screen. Saved/identified are
    # cheap counters bumped on the relevant action instead of being computed
    # by scanning other collections on every profile load.
    identified_count = me.IntField(default=0)
    saved_count = me.IntField(default=0)

    # Streak tracking: consecutive calendar days with at least one
    # identification.
    streak_count = me.IntField(default=0)
    last_active_date = me.DateField(null=True)

    # Daily free-tier search quota. Reset automatically whenever the
    # calendar day changes (see `daily_searches_remaining`/`record_search`)
    # rather than needing a separate scheduled reset job.
    daily_search_count = me.IntField(default=0)
    daily_search_date = me.DateField(null=True)

    meta = {
        "collection": "users",
        "indexes": ["google_id", "email"],
    }

    # DRF's IsAuthenticated permission checks request.user.is_authenticated.
    # Our User is a MongoEngine document, not a Django auth model, so we
    # declare this explicitly. It's always True because our JWTAuthentication
    # class only sets request.user when a valid token is present — unauthenticated
    # requests leave request.user as None, so this property is never reached
    # on an unauthenticated request.
    is_authenticated = True

    FREE_DAILY_SEARCH_LIMIT = 20

    def touch_streak(self):
        """Call once per successful identification. Updates streak_count
        based on calendar-day deltas (UTC)."""
        today = datetime.datetime.utcnow().date()
        if self.last_active_date == today:
            return  # already counted today
        if self.last_active_date == today - datetime.timedelta(days=1):
            self.streak_count += 1
        else:
            self.streak_count = 1
        self.last_active_date = today

    def is_pro(self) -> bool:
        if self.plan != "Pro":
            return False
        if self.plan_expires_at and self.plan_expires_at < datetime.datetime.utcnow():
            return False
        return True

    def _roll_daily_quota_if_new_day(self):
        today = datetime.datetime.utcnow().date()
        if self.daily_search_date != today:
            self.daily_search_count = 0
            self.daily_search_date = today

    def daily_searches_remaining(self) -> int | None:
        """Returns None for Pro (unlimited), otherwise the number of free
        searches left today."""
        if self.is_pro():
            return None
        self._roll_daily_quota_if_new_day()
        return max(0, self.FREE_DAILY_SEARCH_LIMIT - self.daily_search_count)

    def has_search_quota(self) -> bool:
        remaining = self.daily_searches_remaining()
        return remaining is None or remaining > 0

    def record_search(self):
        """Call once per identify attempt (matched or not — searching
        itself is the metered action, same as the existing "20 searches
        per day" copy on the Subscription screen implies)."""
        if self.is_pro():
            return
        self._roll_daily_quota_if_new_day()
        self.daily_search_count += 1

    def to_public_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "avatar": _resolve_avatar_url(self.avatar),
            "plan": "Pro" if self.is_pro() else "Free",
            "planExpiresAt": (
                int(self.plan_expires_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                if self.plan_expires_at
                else None
            ),
            "hasPassword": bool(self.password_hash),
            "dailySearchesRemaining": self.daily_searches_remaining(),
            "dailySearchLimit": self.FREE_DAILY_SEARCH_LIMIT,
            "stats": {
                "identified": self.identified_count,
                "saved": self.saved_count,
                "streak": self.streak_count,
            },
        }


class RefreshToken(me.Document):
    """Server-side allowlist of issued refresh tokens, so logout/rotation
    can actually revoke a token instead of only relying on JWT expiry."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    token_jti = me.StringField(required=True, unique=True)
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    expires_at = me.DateTimeField(required=True)
    revoked = me.BooleanField(default=False)

    meta = {
        "collection": "refresh_tokens",
        "indexes": ["user_id", "token_jti"],
    }


class PasswordResetToken(me.Document):
    """One-time token for the email/password 'forgot password' flow."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    token_hash = me.StringField(required=True, unique=True)
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)
    expires_at = me.DateTimeField(required=True)
    used = me.BooleanField(default=False)

    meta = {
        "collection": "password_reset_tokens",
        "indexes": ["user_id", "token_hash"],
    }
