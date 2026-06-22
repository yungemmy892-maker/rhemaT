import datetime
import hashlib
import secrets

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.avatars import AvatarUploadError, save_avatar
from users.models import PasswordResetToken, RefreshToken, User

from .google_oauth import GoogleAuthError, verify_google_id_token
from .passwords import hash_password, verify_password
from .serializers import (
    ChangePasswordSerializer,
    EmailLoginSerializer,
    EmailRegisterSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    RefreshSerializer,
    ResetPasswordSerializer,
    UpdateProfileSerializer,
)
from .tokens import TokenError, decode_token, issue_token_pair, revoke_refresh_token


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

        if user is None:
            user = User(google_id=google_id, email=email, name=name, avatar=avatar)
        else:
            user.google_id = google_id
            user.name = name
            user.avatar = avatar
        user.last_login_at = datetime.datetime.utcnow()
        user.save()

        tokens = issue_token_pair(user)
        return Response({"user": user.to_public_dict(), **tokens}, status=status.HTTP_200_OK)


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
                {"error": {"code": 409, "message": "An account with this email already exists."}},
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

        tokens = issue_token_pair(user)
        return Response(
            {"user": user.to_public_dict(), **tokens}, status=status.HTTP_201_CREATED
        )


class EmailLoginView(APIView):
    """
    POST /api/v1/auth/login/
    Body: { "email": "...", "password": "..." }
    Matches the Auth screen's "Sign in" tab fields exactly.
    """

    permission_classes = [AllowAny]

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

        tokens = issue_token_pair(user)
        return Response({"user": user.to_public_dict(), **tokens}, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Body: { "email": "..." }

    Issues a one-time reset token. NOTE: the current frontend's "Forgot
    password?" button has no onClick handler (it's a no-op in the existing
    UI), so nothing calls this endpoint yet — it exists so password reset
    can be wired up later without backend changes. Always returns 204
    regardless of whether the email exists, to avoid leaking account
    existence.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects(email=serializer.validated_data["email"]).first()

        if user is not None:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            PasswordResetToken(
                user_id=str(user.id),
                token_hash=token_hash,
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            ).save()
            # In production this token would be emailed to the user via a
            # transactional email provider rather than returned directly.

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/ — { "token": "...", "new_password": "..." }"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token_hash = hashlib.sha256(data["token"].encode()).hexdigest()
        record = PasswordResetToken.objects(token_hash=token_hash).first()
        if (
            record is None
            or record.used
            or record.expires_at < datetime.datetime.utcnow()
        ):
            return Response(
                {"error": {"code": 400, "message": "Reset link is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects(id=record.user_id).first()
        if user is None:
            return Response(
                {"error": {"code": 400, "message": "Reset link is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.password_hash = hash_password(data["new_password"])
        user.save()
        record.used = True
        record.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    Body: { "refresh_token": "..." }
    Returns a fresh access token (and rotates the refresh token).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["refresh_token"]

        try:
            payload = decode_token(token, expected_type="refresh")
        except TokenError as exc:
            return Response(
                {"error": {"code": 401, "message": str(exc)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        record = RefreshToken.objects(token_jti=payload["jti"]).first()
        if not record or record.revoked or record.expires_at < datetime.datetime.utcnow():
            return Response(
                {"error": {"code": 401, "message": "Refresh token is no longer valid."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = User.objects(id=payload["sub"]).first()
        if user is None:
            return Response(
                {"error": {"code": 401, "message": "User no longer exists."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Rotate: revoke the old refresh token, issue a new pair.
        revoke_refresh_token(payload["jti"])
        tokens = issue_token_pair(user)
        return Response(tokens, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — revokes the supplied refresh token."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("refresh_token")
        if token:
            try:
                payload = decode_token(token, expected_type="refresh")
                revoke_refresh_token(payload["jti"])
            except TokenError:
                pass  # already invalid/expired — nothing to revoke
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        return Response(status=status.HTTP_204_NO_CONTENT)


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
                    {"error": {"code": 401, "message": "Current password is incorrect."}},
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
                {"error": {"code": 400, "message": "No file uploaded — expected field 'avatar'."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_path = save_avatar(str(request.user.id), uploaded_file, request.user.avatar)
        except AvatarUploadError as exc:
            return Response({"error": {"code": 400, "message": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

        request.user.avatar = new_path
        request.user.save()
        return Response(request.user.to_public_dict(), status=status.HTTP_200_OK)
