"""Auth dependency: JWKS primary path + legacy HS256 fallback."""

from __future__ import annotations

import time
import uuid
from typing import Any

import jwt
import pytest

from app.core.auth import _decode_supabase_token
from app.core.config import Settings


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "supabase_url": "https://example.supabase.co",
        "supabase_jwt_secret": "test-supabase-jwt-secret",
        "llm_provider": "gemini",
        "gemini_api_key": "test-gemini-key",
    }
    base.update(overrides)
    return Settings(**base)


def test_decode_legacy_hs256_token() -> None:
    user_id = uuid.uuid4()
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "iat": now,
            "exp": now + 3600,
            "role": "authenticated",
        },
        "test-supabase-jwt-secret",
        algorithm="HS256",
    )

    payload = _decode_supabase_token(token, _settings())
    assert payload["sub"] == str(user_id)


def test_decode_hs256_without_secret_fails() -> None:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "iat": now,
            "exp": now + 3600,
        },
        "test-supabase-jwt-secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.PyJWTError):
        _decode_supabase_token(token, _settings(supabase_jwt_secret=None))
