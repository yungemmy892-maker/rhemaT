import datetime
import uuid

import jwt
from django.conf import settings

from users.models import RefreshToken


def _now():
    return datetime.datetime.utcnow()


def issue_access_token(user) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "type": "access",
        "iat": _now(),
        "exp": _now() + settings.JWT_ACCESS_TTL,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def issue_refresh_token(user) -> str:
    jti = uuid.uuid4().hex
    expires_at = _now() + settings.JWT_REFRESH_TTL
    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "jti": jti,
        "iat": _now(),
        "exp": expires_at,
    }
    RefreshToken(user_id=str(user.id), token_jti=jti, expires_at=expires_at).save()
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def issue_token_pair(user) -> dict:
    return {
        "access_token": issue_access_token(user),
        "refresh_token": issue_refresh_token(user),
        "token_type": "Bearer",
        "expires_in": int(settings.JWT_ACCESS_TTL.total_seconds()),
    }


class TokenError(Exception):
    pass


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired.")
    except jwt.InvalidTokenError:
        raise TokenError("Token is invalid.")

    if payload.get("type") != expected_type:
        raise TokenError("Incorrect token type.")
    return payload


def revoke_refresh_token(jti: str):
    RefreshToken.objects(token_jti=jti).update(set__revoked=True)


def is_refresh_token_valid(jti: str) -> bool:
    record = RefreshToken.objects(token_jti=jti).first()
    return bool(record and not record.revoked and record.expires_at > _now())
