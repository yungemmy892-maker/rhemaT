"""
Fired once, right when a brand-new VerseID account is created — from either
EmailRegisterView (email/password sign-up) or GoogleLoginView (a user's
first-ever Google sign-in). Adds a "Welcome" card to the in-app
Notifications feed and sends a matching HTML welcome email.

Best-effort by design: a slow/broken SMTP provider must never fail account
creation, so both steps are individually swallowed and logged rather than
raised.
"""
import logging

from .email import send_welcome_email
from .models import Notification

logger = logging.getLogger(__name__)


def send_welcome(user) -> None:
    first_name = (user.name or "there").split(" ")[0]

    try:
        Notification(
            user_id=str(user.id),
            kind="welcome",
            title="Welcome to VerseID \U0001F44B",
            body=(
                "Tap the mic and point it at any verse being read aloud — "
                "we'll tell you exactly what it is."
            ),
        ).save()
    except Exception:
        logger.exception("Failed to create welcome notification for user %s", user.id)

    try:
        send_welcome_email(user.email, first_name)
    except Exception:
        logger.exception("Failed to send welcome email to %s", user.email)
