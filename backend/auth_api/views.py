import datetime
import hashlib
import hmac
import logging
import secrets

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.email import send_password_reset_email
from notifications.welcome import send_welcome
from users.avatars import AvatarUploadError, save_avatar
from users.models import PasswordResetToken, RefreshToken, User

from .cookies import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    generate_csrf_token,
    set_auth_cookies,
    verify_csrf,
)
from .google_oauth import GoogleAuthError, verify_google_id_token
from .passwords import hash_password, verify_password
from .serializers import (
    ChangePasswordSerializer,
    EmailLoginSerializer,
    EmailRegisterSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    ResetPasswordSerializer,
    UpdateProfileSerializer,
    VerifyResetCodeSerializer,
)
from .tokens import TokenError, decode_token, issue_token_pair, revoke_refresh_token

logger = logging.getLogger(__name__)

# How many wrong code attempts are allowed before a code is locked out —
# guards against brute-forcing a 6-digit (1-in-a-million) code.
MAX_CODE_ATTEMPTS = 5
CODE_TTL_MINUTES = 10


def _tokens_response(body: dict, user, status_code: int) -> Response:
    """Issue a fresh access+refresh token pair for `user`, merge the
    access-token fields into `body`, and set the refresh + CSRF cookies on
    the response. The refresh token itself never enters the response body
    or reaches frontend JS — see auth_api/cookies.py. Used by every
    endpoint that starts or rotates a session (register/login/google/
    refresh)."""
    tokens = issue_token_pair(user)
    refresh_token = tokens.pop("refresh_token")
    response = Response({**body, **tokens}, status=status_code)
    set_auth_cookies(
        response,
        refresh_token=refresh_token,
        csrf_token=generate_csrf_token(),
        max_age_seconds=int(settings.JWT_REFRESH_TTL.total_seconds()),
    )
    return response


def _csrf_failure() -> Response:
    return Response(
        {"error": {"code": 403, "message": "CSRF check failed."}},
        status=status.HTTP_403_FORBIDDEN,
    )


def _latest_active_token(user_id: str) -> PasswordResetToken | None:
    return (
        PasswordResetToken.objects(user_id=user_id, used=False)
        .order_by("-created_at")
        .first()
    )


def _code_invalid_response() -> Response:
    return Response(
        {"error": {"code": 400, "message": "That code is invalid or has expired."}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _avatar_fallback(name: str) -> str:
    seed = (name or "user").split(" ")[0]
    return f"https://api.dicebear.com/9.x/notionists/svg?seed={seed}&backgroundColor=ede9fe"


def _name_from_email(email: str) -> str:
    local = email.split("@")[0]
    words = local.replace(".", " ").replace("_", " ").split()
    return " ".join(w.capitalize() for w in words) or "Friend"


class GoogleLoginView(APIView):
    """
    POST /api/v1/auth/google/
    Body: { "id_token": "<google id token>" }

    Verifies the Google ID token, creates the user on first sign-in
    (matching the frontend's existing signInGoogle() UX), and returns a
    JWT access/refresh pair.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            claims = verify_google_id_token(serializer.validated_data["id_token"])
        except GoogleAuthError as exc:
            return Response(
                {"error": {"code": 401, "message": str(exc)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        google_id = claims["sub"]
        email = claims["email"]
        name = claims.get("name") or email.split("@")[0]
        avatar = claims.get("picture") or _avatar_fallback(name)

        user = User.objects(google_id=google_id).first()
        if user is None:
            # Also guard against an email collision from a previous,
            # differently-provisioned account (e.g. registered by
            # email/password first, now also linking Google).
            user = User.objects(email=email).first()

        is_new_user = user is None
        if is_new_user:
            user = User(google_id=google_id, email=email, name=name, avatar=avatar)
        else:
            # Only link the google_id here — deliberately NOT re-setting
            # name/avatar for a returning user. This used to overwrite
            # whatever the user had customized via Edit Profile with
            # whatever their Google account's name/photo currently is,
            # every single time they logged back in via Google — a
            # returning login should authenticate, not silently revert
            # profile edits.
            user.google_id = google_id
        user.last_login_at = datetime.datetime.utcnow()
        user.save()

        if is_new_user:
            send_welcome(user)

        return _tokens_response(
            {"user": user.to_public_dict()}, user, status.HTTP_200_OK
        )


class EmailRegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Body: { "name": "...", "email": "...", "password": "..." }
    Matches the Auth screen's "Register" tab fields exactly.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects(email=data["email"]).first() is not None:
            return Response(
                {
                    "error": {
                        "code": 409,
                        "message": "An account with this email already exists.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        name = data.get("name") or _name_from_email(data["email"])
        user = User(
            email=data["email"],
            name=name,
            avatar=_avatar_fallback(name),
            password_hash=hash_password(data["password"]),
        )
        user.save()
        send_welcome(user)

        return _tokens_response(
            {"user": user.to_public_dict()}, user, status.HTTP_201_CREATED
        )


class EmailLoginView(APIView):
    """
    POST /api/v1/auth/login/
    Body: { "email": "...", "password": "..." }
    Matches the Auth screen's "Sign in" tab fields exactly.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects(email=data["email"]).first()
        invalid = Response(
            {"error": {"code": 401, "message": "Incorrect email or password."}},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        if user is None or not user.password_hash:
            # Don't reveal whether the email exists or was Google-only.
            return invalid
        if not verify_password(data["password"], user.password_hash):
            return invalid

        user.last_login_at = datetime.datetime.utcnow()
        user.save()

        return _tokens_response(
            {"user": user.to_public_dict()}, user, status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Body: { "email": "..." }

    Step 1 of the reset flow: issues a 6-digit code, emails it, and
    invalidates any previously-issued unused code for this user so only the
    latest one is valid. Always returns 204 regardless of whether the email
    exists, to avoid leaking account existence.
    """

    permission_classes = [AllowAny]
    throttle_scope = "forgot-password"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects(email=serializer.validated_data["email"]).first()

        if user is not None:
            PasswordResetToken.objects(user_id=str(user.id), used=False).update(
                set__used=True
            )

            code = f"{secrets.randbelow(1_000_000):06d}"
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            PasswordResetToken(
                user_id=str(user.id),
                token_hash=code_hash,
                expires_at=datetime.datetime.utcnow()
                + datetime.timedelta(minutes=CODE_TTL_MINUTES),
            ).save()

            try:
                send_password_reset_email(user.email, user.name.split(" ")[0], code)
            except Exception:
                # The HTTP response must stay a generic 204 regardless (never
                # leak email delivery failures to the client — that's also
                # how account-enumeration is avoided) but swallowing this
                # with a bare `pass` made real SMTP misconfiguration
                # completely invisible. Log it so it actually shows up in
                # the server console/logs during development.
                logger.exception(
                    "Failed to send password reset email to %s", user.email
                )

        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyResetCodeView(APIView):
    """
    POST /api/v1/auth/verify-reset-code/
    Body: { "email": "...", "code": "123456" }

    Step 2 of the reset flow — lets the frontend confirm the code before
    showing the "new password" screen, without consuming the code yet
    (that happens in ResetPasswordView so the code can only be spent once).
    """

    permission_classes = [AllowAny]
    throttle_scope = "verify-reset-code"

    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects(email=data["email"]).first()
        if user is None:
            return _code_invalid_response()

        record = _latest_active_token(str(user.id))
        if record is None or record.expires_at < datetime.datetime.utcnow():
            return _code_invalid_response()
        if record.attempts >= MAX_CODE_ATTEMPTS:
            return _code_invalid_response()

        code_hash = hashlib.sha256(data["code"].encode()).hexdigest()
        if not hmac.compare_digest(record.token_hash, code_hash):
            PasswordResetToken.objects(id=record.id).update(inc__attempts=1)
            return _code_invalid_response()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/
    Body: { "email": "...", "code": "123456", "new_password": "..." }

    Step 3 — re-validates the code (a code is only ever actually consumed
    here, never in VerifyResetCodeView) then updates the password and
    revokes every existing refresh token, signing the user out everywhere
    as a safety measure.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects(email=data["email"]).first()
        if user is None:
            return _code_invalid_response()

        record = _latest_active_token(str(user.id))
        if record is None or record.expires_at < datetime.datetime.utcnow():
            return _code_invalid_response()
        if record.attempts >= MAX_CODE_ATTEMPTS:
            return _code_invalid_response()

        code_hash = hashlib.sha256(data["code"].encode()).hexdigest()
        if not hmac.compare_digest(record.token_hash, code_hash):
            PasswordResetToken.objects(id=record.id).update(inc__attempts=1)
            return _code_invalid_response()

        user.password_hash = hash_password(data["new_password"])
        user.save()

        record.used = True
        record.save()

        # Reset is a credential change — sign the user out of every device.
        RefreshToken.objects(user_id=str(user.id)).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    No body. The refresh token comes from the httpOnly cookie set at
    login/register (see auth_api/cookies.py) — the frontend no longer
    holds it directly. Requires a matching X-CSRF-Token header (double-
    submit check against the companion, JS-readable CSRF cookie) since
    this endpoint trusts a cookie the browser attaches automatically
    rather than a credential the frontend explicitly supplies.
    Returns a fresh access token and rotates the refresh cookie.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not token:
            return Response(
                {"error": {"code": 401, "message": "No refresh token."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_csrf(request):
            return _csrf_failure()

        try:
            payload = decode_token(token, expected_type="refresh")
        except TokenError as exc:
            return Response(
                {"error": {"code": 401, "message": str(exc)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        record = RefreshToken.objects(token_jti=payload["jti"]).first()
        if (
            not record
            or record.revoked
            or record.expires_at < datetime.datetime.utcnow()
        ):
            return Response(
                {
                    "error": {
                        "code": 401,
                        "message": "Refresh token is no longer valid.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = User.objects(id=payload["sub"]).first()
        if user is None:
            return Response(
                {"error": {"code": 401, "message": "User no longer exists."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Rotate: revoke the old refresh token, issue a new pair (sets new
        # refresh + CSRF cookies on the response).
        revoke_refresh_token(payload["jti"])
        return _tokens_response({}, user, status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/ — revokes the refresh token carried by the
    httpOnly cookie and clears both auth cookies. Requires a matching
    X-CSRF-Token header, same as /refresh/ (see auth_api/cookies.py).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if token:
            if not verify_csrf(request):
                return _csrf_failure()
            try:
                payload = decode_token(token, expected_type="refresh")
                revoke_refresh_token(payload["jti"])
            except TokenError:
                pass  # already invalid/expired — nothing to revoke

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    """
    GET    /api/v1/auth/me/ — current authenticated user.
    PATCH  /api/v1/auth/me/ — update profile fields (currently: name).
    DELETE /api/v1/auth/me/ — delete account.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(request.user.to_public_dict())

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data.get("name")
        if name:
            request.user.name = name
            request.user.save()
        return Response(request.user.to_public_dict())

    def delete(self, request):
        """Account deletion, matching the existing Settings screen action."""
        user_id = str(request.user.id)
        RefreshToken.objects(user_id=user_id).delete()
        request.user.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Body: { "current_password": "...", "new_password": "..." }

    For authenticated users changing their password from within the app
    (Profile > Edit profile), as opposed to the unauthenticated
    forgot/reset-password flow above. If the account has no password yet
    (Google-only sign-up), `current_password` may be omitted to set one
    for the first time.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        if user.password_hash:
            current = data.get("current_password")
            if not current or not verify_password(current, user.password_hash):
                return Response(
                    {
                        "error": {
                            "code": 401,
                            "message": "Current password is incorrect.",
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        user.password_hash = hash_password(data["new_password"])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvatarUploadView(APIView):
    """
    POST /api/v1/auth/avatar/
    Multipart form upload, field name "avatar". Accepts an image from
    either a file picker ("choose from gallery") or a camera capture
    ("take a photo") — both arrive identically as a single uploaded file,
    the distinction is purely in the frontend's <input> attributes.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("avatar")
        if uploaded_file is None:
            return Response(
                {
                    "error": {
                        "code": 400,
                        "message": "No file uploaded — expected field 'avatar'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_path = save_avatar(
                str(request.user.id), uploaded_file, request.user.avatar
            )
        except AvatarUploadError as exc:
            return Response(
                {"error": {"code": 400, "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.avatar = new_path
        request.user.save()
        return Response(request.user.to_public_dict(), status=status.HTTP_200_OK)
