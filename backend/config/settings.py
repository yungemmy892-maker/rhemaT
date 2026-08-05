"""
Django settings for the VerseID backend.

"""

import os
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from mongoengine import connect

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-change-me")
# Defaults to False (not True) deliberately — DEBUG=True in production
# leaks stack traces, settings values, and SQL/query internals to anyone
# who can trigger a 500. Local dev sets DJANGO_DEBUG=True explicitly in
# .env, so this only matters as a fail-safe for an environment that
# forgot to set it at all — which should be safe, not verbose, by default.
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,api.verseid.top,rhemat.pxxl.run,127.0.0.1",
    ).split(",")
    if host.strip()
]
# Refuse to start with an empty or wildcard ALLOWED_HOSTS outside of DEBUG.
# ALLOWED_HOSTS is Django's actual defense against Host-header attacks
# (cache poisoning, password-reset-link poisoning); "fixing" a
# DisallowedHost error by setting this to "*" silently defeats that
# defense rather than resolving whatever the real misconfiguration was.
if not DEBUG and (not ALLOWED_HOSTS or ALLOWED_HOSTS == [""] or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set to a specific, comma-separated "
        "list of hostnames when DJANGO_DEBUG=False (e.g. "
        "'api.verseid.top,rhemat.pxxl.run'). Refusing to start with an "
        "empty or wildcard value in production."
    )

INSTALLED_APPS = [
    # Deliberately no django.contrib.admin / auth / sessions / contenttypes:
    # this project has no relational DB and no Django-auth User model.
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "users",
    "auth_api",
    "bible",
    "search",
    "preferences",
    "notifications",
    "billing",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# No relational DB. A dummy sqlite backend is kept ONLY because Django's
# internals expect DATABASES to exist; nothing ever touches it.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "unused.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# User-uploaded files (currently just profile avatars). Served by Django
# itself in development via the urls.py static() helper; in production,
# serve this directory with your web server/CDN instead (see README).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "avatars")

# Base URL used to build absolute avatar URLs returned by the API (e.g.
# "http://localhost:8000"). Needed because the frontend may be served from
# a different origin than the backend.
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# MongoDB (MongoEngine)
# ---------------------------------------------------------------------------

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/verseid")
connect(
    host=MONGO_URI,
    retryWrites=True,
    retryReads=True,
    maxPoolSize=int(os.environ.get("MONGO_MAX_POOL_SIZE", "10")),
    minPoolSize=int(os.environ.get("MONGO_MIN_POOL_SIZE", "0")),
    # Idle pooled connections older than this get closed rather than kept
    # open forever — matters more now that multiple processes each hold a
    # pool, since Atlas (and most managed Mongo) will also enforce its own
    # idle-connection ceiling server-side.
    maxIdleTimeMS=int(os.environ.get("MONGO_MAX_IDLE_TIME_MS", "60000")),
    # Fail fast instead of hanging a request/worker forever if Mongo is
    # unreachable — was unset before, so pymongo's 30s wire-protocol default
    # applied everywhere, including gunicorn's own request timeout window.
    serverSelectionTimeoutMS=int(
        os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "30000")
    ),
)

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "auth_api.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    # DRF defaults UNAUTHENTICATED_USER to django.contrib.auth.models.AnonymousUser
    # which pulls in django.contrib.contenttypes — not in INSTALLED_APPS since this
    # project uses MongoDB only. Setting to None tells DRF to leave request.user
    # unset for unauthenticated requests instead of using Django's AnonymousUser.
    "UNAUTHENTICATED_USER": None,
    # Rate limiting (audit H1): unthrottled auth endpoints previously allowed
    # unlimited password guessing / reset-code email-bombing. ScopedRateThrottle
    # keys by client IP by default, which is what we want here since these
    # endpoints are hit pre-authentication (no user to key on yet).
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "forgot-password": "3/hour",
        "verify-reset-code": "10/hour",
        # IdentifyView (search/views.py) — each call hits FAISS and, for
        # semantic re-rank, the Hugging Face Inference API, which is both
        # a real cost and a real per-token rate limit upstream. The daily
        # search quota (has_search_quota()) caps how much a user can do
        # overall, but doesn't stop them from firing 50 requests in the
        # same second and burning through it against a slow/rate-limited
        # upstream — this caps the rate, not just the daily total.
        "search": "20/min",
    },
}

# ---------------------------------------------------------------------------
# JWT (hand-rolled with PyJWT — SimpleJWT assumes the Django ORM User model,
# which this project does not use since all users live in MongoDB)
# ---------------------------------------------------------------------------

JWT_SECRET = os.environ.get("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TTL = timedelta(minutes=int(os.environ.get("JWT_ACCESS_TTL_MIN", "15")))
JWT_REFRESH_TTL = timedelta(days=int(os.environ.get("JWT_REFRESH_TTL_DAYS", "30")))

# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

# ---------------------------------------------------------------------------
# Gemini + Groq (interface language) — bible/translate_service.py
# Gemini is tried first; Groq is the fallback if Gemini is unset, fails, or
# errors. Leave both unset to run English-only UI; translated strings just
# fall back to English.
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# ---------------------------------------------------------------------------
# Hugging Face Inference API (semantic search — search/embeddings.py, search/faiss_index.py)
# Free token from https://huggingface.co/settings/tokens. Leave unset to
# run with lexical-only matching; semantic re-rank silently no-ops without it.
# ---------------------------------------------------------------------------

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# ---------------------------------------------------------------------------
# Admin dashboard (analytics app) — a single shared secret, checked against
# the X-Admin-Key header. See analytics/views.py's HasAdminKey.
# ---------------------------------------------------------------------------

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# ---------------------------------------------------------------------------
# Paystack (Nigerian payment processor for Pro subscriptions)
# Get keys from https://dashboard.paystack.com/#/settings/developers
# ---------------------------------------------------------------------------

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")

# NGN pricing (kobo = smallest unit, 100 kobo = ₦1)
# Monthly: ₦1,000  |  Annual: ₦9,000  (saves ₦3,000 vs monthly)
PLAN_MONTHLY_KOBO = 100_000  # ₦1,000
PLAN_ANNUAL_KOBO = 900_000  # ₦9,000

# ---------------------------------------------------------------------------
# Web Push (VAPID) — for the daily verse-of-the-day push notification.
# Generate a keypair with: python manage.py generate_vapid_keys
# ---------------------------------------------------------------------------

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:rhema.trem@gmail.com")

# ---------------------------------------------------------------------------
# Email (fallback delivery for the daily verse notification when a user has
# no active push subscription, e.g. hasn't granted browser notification
# permission). Defaults to Django's console backend so `send_daily_verse`
# works out of the box in development without any SMTP setup — switch
# EMAIL_BACKEND in .env for real delivery.
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "VerseID <noreply@verseid.app>"
)

EMAIL_TIMEOUT = (
    10  # seconds — fail fast instead of hanging on a dead/unreachable SMTP host
)

# Base URL of the deployed frontend, used to build links inside transactional
# emails (welcome email CTA, future password-reset links, etc).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://verseid.top")

# ---------------------------------------------------------------------------
# CORS — frontend dev server(s)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "https://verseid.top,https://www.verseid.top",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
# The refresh/logout endpoints require the frontend to echo a CSRF cookie's
# value back in this header (see auth_api/cookies.py) — corsheaders drops
# any header not on this list before it reaches the view, so it has to be
# added explicitly to the defaults rather than replacing them.
CORS_ALLOW_HEADERS = [*default_headers, "x-csrf-token"]

# ---------------------------------------------------------------------------
# Auth cookies (httpOnly refresh token + JS-readable CSRF token) — see
# auth_api/cookies.py for the full rationale.
# ---------------------------------------------------------------------------

# Domain attribute for both cookies. Leave unset for local dev — frontend
# and backend are different ports of the SAME host (localhost) there, so a
# host-only cookie (no explicit Domain) already works. In production the
# frontend (verseid.top) and backend (api.verseid.top) are a subdomain
# split of the same registrable domain, so set this to ".verseid.top" —
# note the leading dot, and note it's the PARENT domain, not the backend's
# own hostname — so the browser will attach the cookie to requests aimed
# at api.verseid.top even though it was set from that same host.
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "")

# Secure=True means these cookies are only ever sent over HTTPS. Defaults
# to the inverse of DEBUG since local dev runs on plain HTTP, where a
# Secure cookie would silently never be attached. Always True in
# production — verseid.top and api.verseid.top are both HTTPS-only.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "False" if DEBUG else "True") == "True"

# ---------------------------------------------------------------------------
# Redis — cache backend AND Celery broker/result backend, sharing one
# instance on two different logical DBs so a cache flush can never touch
# the task queue (and vice versa). REDIS_URL must be the bare connection
# string with NO trailing /<db-number> — this file appends the DB index
# itself. Defaults to a local Redis for development.
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL")

# A silent localhost fallback in production means Celery/cache just hang or
# fail per-request with a connection-refused error the first time something
# actually needs Redis — hours or days after the real problem (a forgotten
# env var) was introduced. Fail loudly at startup instead.
if not DEBUG and not REDIS_URL:
    raise ImproperlyConfigured(
        "REDIS_URL must be set when DJANGO_DEBUG=False — it's required for "
        "the cache backend and as the Celery broker/result backend (see "
        "config/celery.py). There is no safe default for it in production."
    )

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
        "TIMEOUT": 300,
    },
}

# IGNORE_EXCEPTIONS above means a Redis outage no longer breaks requests —
# but it would also mean it fails completely silently otherwise. This
# makes django-redis log every ignored exception (at ERROR, via the
# "django_redis.cache" logger configured below) so an actual outage is
# still visible in production logs instead of just quietly degrading
# forever.
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# ---------------------------------------------------------------------------
# Celery — background/scheduled jobs (config/celery.py). Replaces the old
# in-process scheduler threads in billing/ and notifications/: those ran
# once per gunicorn WORKER (see git history), so more than one worker meant
# charge_renewals / send_daily_verse firing multiple times on the same
# schedule. Celery Beat is a single dedicated process regardless of gunicorn
# worker count, which is what actually makes it safe to run >1 worker now.
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
# Belt-and-suspenders: cap how long any single task run may hang, so a
# stuck Paystack/push/email call can't wedge a worker slot forever.
# 30 min (not the original 10) gives charge_renewals real headroom on a
# day with an unusually large batch of due subscriptions, each making a
# live Paystack API call. SOFT_TIME_LIMIT fires 60s earlier and raises an
# exception inside the task instead of SIGKILL-ing it outright, so a task
# gets one chance to stop cleanly (e.g. finish logging what it already
# charged) before the hard limit ends it mid-operation.
CELERY_TASK_TIME_LIMIT = 60 * 30
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 29

# ---------------------------------------------------------------------------
# Security headers — X-Frame-Options and HSTS are read directly by
# XFrameOptionsMiddleware / SecurityMiddleware (both already installed
# above), so these are plain settings, not middleware. CSP and
# X-XSS-Protection have no Django setting to read — see
# config/middleware.py's SecurityHeadersMiddleware for those two.
# ---------------------------------------------------------------------------

# Already Django's default when XFrameOptionsMiddleware is installed —
# set explicitly anyway so it's documented here rather than implicit.
X_FRAME_OPTIONS = "DENY"

# HSTS tells the browser "never try plain HTTP for this host again, for
# the next N seconds" — genuinely dangerous to get wrong, since a browser
# that's already seen this header will refuse HTTP even if you need to
# roll back.
SECURE_HSTS_SECONDS = int(
    os.environ.get("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
)
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "False") == "True"

# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} — {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        # Uncaught view exceptions (500s) — always surfaced at ERROR,
        # DEBUG or not, since this is the actual "something broke" signal
        # every other logger's level is tuned to avoid drowning out.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
