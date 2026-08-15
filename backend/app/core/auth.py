"""Supabase JWT authentication for API routes.

Primary path: asymmetric keys (ES256/RS256) via the project's JWKS endpoint.
Optional fallback: legacy HS256 shared secret when ``SUPABASE_JWT_SECRET`` is set.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=False)
_ASYMMETRIC_ALGS = frozenset({"ES256", "RS256"})


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Authenticated caller identified by Supabase ``auth.users`` id (JWT ``sub``)."""

    id: uuid.UUID


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    # Public keys only — matches Current ECC/RSA signing keys in the dashboard.
    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def _issuer(settings: Settings) -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _decode_supabase_token(token: str, settings: Settings) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")
    issuer = _issuer(settings)

    if alg in _ASYMMETRIC_ALGS:
        signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
        )

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError(
                "HS256 token received but SUPABASE_JWT_SECRET is not configured"
            )
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=issuer,
        )

    raise jwt.InvalidTokenError(f"Unsupported JWT algorithm: {alg}")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    """Validate a Supabase access token (JWKS / ES256 preferred) and return the caller."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing or invalid authorization token")

    try:
        payload = _decode_supabase_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid or expired authorization token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise _unauthorized("Invalid or expired authorization token")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise _unauthorized("Invalid or expired authorization token") from exc

    return CurrentUser(id=user_id)


# DI alias used by document/chat routes (Phase 7 Steps 3–4).
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
