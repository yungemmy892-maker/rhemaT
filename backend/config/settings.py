"""
Django settings for the VerseID backend.

"""

import os
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from dotenv import load_dotenv
from mongoengine import connect

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,api.verseid.top,rhemat.pxxl.run,127.0.0.1").split(",")

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
    # Pool size is PER PROCESS — every gunicorn worker and every Celery
    # worker process gets its own pool of this size, so the real ceiling on
    # simultaneous MongoDB connections is roughly
    # maxPoolSize x (gunicorn workers + celery worker concurrency).
    # Defaults to 10, which comfortably fits a handful of processes under
    # a typical Atlas shared-tier connection limit — raise MONGO_MAX_POOL_SIZE
    # explicitly if profiling shows requests queuing on pool checkout.
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
    serverSelectionTimeoutMS=int(os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "10000")),
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
PLAN_MONTHLY_KOBO = 100_000    # ₦1,000
PLAN_ANNUAL_KOBO = 900_000     # ₦9,000

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
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "VerseID <noreply@verseid.app>")

# Base URL of the deployed frontend, used to build links inside transactional
# emails (welcome email CTA, future password-reset links, etc).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://verseid.top")

# ---------------------------------------------------------------------------
# CORS — frontend dev server(s)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://verseid.top,https://www.verseid.top,https://verseid.top,https://www.verseid.top",
).split(",")
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

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        # Per-endpoint TIMEOUT is set explicitly at each cache.set() call
        # (see bible/views.py) since cache lifetime varies a lot by what's
        # being cached (Bible text is static; verse-of-day changes daily).
        # This is just the fallback for any cache.set() that doesn't pass one.
        "TIMEOUT": 300,
    },
}

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
CELERY_TASK_TIME_LIMIT = 60 * 10