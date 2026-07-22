import hmac
import secrets

from django.conf import settings

REFRESH_COOKIE_NAME = "verseid_refresh"
CSRF_COOKIE_NAME = "verseid_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Scoped to /api/v1/auth/ — the browser only attaches these cookies to
# requests under this path, so they're never sent to /bible/, /search/,
# billing, etc. even though those endpoints share the same domain.
COOKIE_PATH = "/api/v1/auth"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response, *, refresh_token: str, csrf_token: str, max_age_seconds: int
) -> None:
    """Set the refresh + CSRF cookies on an outgoing Response. Call this
    from every endpoint that issues or rotates a refresh token."""
    common = dict(
        max_age=max_age_seconds,
        secure=settings.COOKIE_SECURE,
        samesite="Lax",
        domain=settings.COOKIE_DOMAIN or None,
        path=COOKIE_PATH,
    )
    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, httponly=True, **common)
    # Deliberately NOT httponly — the frontend has to read this one client-side
    # to echo it back in the X-CSRF-Token header.
    response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=False, **common)


def clear_auth_cookies(response) -> None:
    """Delete both cookies. Call this on logout."""
    kwargs = dict(domain=settings.COOKIE_DOMAIN or None, path=COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, **kwargs)
    response.delete_cookie(CSRF_COOKIE_NAME, **kwargs)


def verify_csrf(request) -> bool:
    """Double-submit check: the CSRF cookie's value must match the
    X-CSRF-Token header exactly. Returns False (never raises) so callers
    can turn a failure into whatever 403 response shape they want."""
    cookie_value = request.COOKIES.get(CSRF_COOKIE_NAME)
    header_value = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)
