"""Access and refresh tokens: what `decode_token` accepts and what it refuses."""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.config import settings
from app.core.security import (
    TOKEN_TYPE_ACCESS,
    create_access_token,
    create_token,
    decode_token,
)

pytestmark = pytest.mark.api


def test_an_access_token_decodes_to_its_subject_and_type():
    claims = decode_token(create_access_token("user-1"))
    assert claims is not None
    assert claims["sub"] == "user-1"
    assert claims["type"] == TOKEN_TYPE_ACCESS
    assert claims["jti"]


def test_an_expired_token_is_refused():
    token = create_token("user-1", TOKEN_TYPE_ACCESS, timedelta(seconds=-1))
    assert decode_token(token) is None


def test_a_token_signed_with_another_key_is_refused():
    token = jwt.encode({"sub": "user-1"}, "x" * 64, algorithm=settings.ALGORITHM)
    assert decode_token(token) is None


def test_a_tampered_payload_is_refused():
    header, _payload, signature = create_access_token("user-1").split(".")
    forged = jwt.encode({"sub": "admin"}, "x" * 64, algorithm="HS256").split(".")[1]
    assert decode_token(f"{header}.{forged}.{signature}") is None


def test_an_unsigned_token_is_refused():
    token = jwt.encode({"sub": "admin"}, None, algorithm="none")
    assert decode_token(token) is None


def test_garbage_is_refused():
    assert decode_token("not.a.token") is None
