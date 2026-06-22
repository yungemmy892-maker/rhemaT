from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


class GoogleAuthError(Exception):
    pass


def verify_google_id_token(token: str) -> dict:
    """
    Verifies a Google Sign-In ID token (sent by the frontend's Google
    Identity Services button) and returns the decoded claims.

    Raises GoogleAuthError on any verification failure.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleAuthError(
            "Server is missing GOOGLE_CLIENT_ID — set it in backend/.env."
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise GoogleAuthError(f"Invalid Google token: {exc}")

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleAuthError("Invalid token issuer.")

    if not claims.get("email_verified", False):
        raise GoogleAuthError("Google account email is not verified.")

    return claims
