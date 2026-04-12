"""JWT implementation of ITokenService."""
import os
from datetime import datetime, timedelta, timezone
import jwt
from ...domain.models import User, TokenPair, TokenClaims
from ...domain.ports import ITokenService

_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
_ALGORITHM = "HS256"
_ACCESS_TTL = int(os.getenv("JWT_ACCESS_TTL_MINUTES", "30"))
_REFRESH_TTL = int(os.getenv("JWT_REFRESH_TTL_DAYS", "7"))


class JWTTokenService(ITokenService):
    def create_token_pair(self, user: User) -> TokenPair:
        now = datetime.now(timezone.utc)
        access = jwt.encode(
            {"sub": user.id, "email": user.email, "username": user.username,
             "role": user.role.value, "type": "access", "iat": now,
             "exp": now + timedelta(minutes=_ACCESS_TTL)},
            _SECRET, algorithm=_ALGORITHM,
        )
        refresh = jwt.encode(
            {"sub": user.id, "email": user.email, "username": user.username,
             "role": user.role.value, "type": "refresh", "iat": now,
             "exp": now + timedelta(days=_REFRESH_TTL)},
            _SECRET, algorithm=_ALGORITHM,
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    def validate_access_token(self, token: str) -> TokenClaims:
        return self._decode(token, expected_type="access")

    def decode_refresh_token(self, token: str) -> TokenClaims:
        return self._decode(token, expected_type="refresh")

    def _decode(self, token: str, expected_type: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
            if payload.get("type") != expected_type:
                return TokenClaims(user_id="", email="", role="", valid=False, error="Wrong token type")
            return TokenClaims(
                user_id=payload["sub"],
                email=payload["email"],
                role=payload["role"],
                valid=True,
            )
        except jwt.ExpiredSignatureError:
            return TokenClaims(user_id="", email="", role="", valid=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            return TokenClaims(user_id="", email="", role="", valid=False, error=str(e))
