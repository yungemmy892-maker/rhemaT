"""
Django settings for the VerseID backend.

"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from mongoengine import connect

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
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

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# User-uploaded files (currently just profile avatars). Served by Django
# itself in development via the urls.py static() helper; in production,
# serve this directory with your web server/CDN instead (see README).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Base URL used to build absolute avatar URLs returned by the API (e.g.
# "http://localhost:8000"). Needed because the frontend may be served from
# a different origin than the backend.
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# MongoDB (MongoEngine)
# ---------------------------------------------------------------------------

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/verseid")
connect(host=MONGO_URI)

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
    "UNAUTHENTICATED_USER": None,
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
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# ---------------------------------------------------------------------------
# Paystack (Nigerian payment processor for Pro subscriptions)
# Get keys from https://dashboard.paystack.com/#/settings/developers
# ---------------------------------------------------------------------------

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")

# NGN pricing (kobo = smallest unit, 100 kobo = ₦1)
# Monthly: ₦2,500  |  Annual: ₦20,000  (saves ≈33%)
PLAN_MONTHLY_KOBO = 250_000    # ₦2,500
PLAN_ANNUAL_KOBO = 2_000_000   # ₦20,000

# ---------------------------------------------------------------------------
# Web Push (VAPID) — for the daily verse-of-the-day push notification.
# Generate a keypair with: python manage.py generate_vapid_keys
# ---------------------------------------------------------------------------

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")

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

# ---------------------------------------------------------------------------
# CORS — frontend dev server(s)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
).split(",")
CORS_ALLOW_CREDENTIALS = True
