from rest_framework import authentication, exceptions

from users.models import User

from .tokens import TokenError, decode_token


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Expects: Authorization: Bearer <access_token>

    Populates request.user with a MongoEngine User document (not Django's
    auth.User) since this project has no relational user table.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        token = parts[1]
        try:
            payload = decode_token(token, expected_type="access")
        except TokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc))

        user = User.objects(id=payload["sub"]).first()
        if user is None:
            raise exceptions.AuthenticationFailed("User no longer exists.")

        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
