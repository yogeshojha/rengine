from __future__ import annotations

import uuid

import pytest
from fastapi import Response
from pydantic import ValidationError
from starlette.requests import Request

from app.api.v1.auth import (
    AUTH_COOKIES,
    REFRESH_TOKEN_COOKIE,
    LoginRequest,
    PasswordChangeRequest,
    UsernameChangeRequest,
    login,
    refresh_access_token,
    router,
)
from app.core.security import create_refresh_token, hash_password
from shared.models.user import User

pytestmark = pytest.mark.api

STRONG = "Vq7#mT9!pLx2@wRz"


def _cookies(response: Response) -> set[str]:
    return {
        value.decode().split("=", 1)[0]
        for name, value in response.raw_headers
        if name == b"set-cookie"
    }


async def _account(session) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"auth{tag}",
        email=f"auth{tag}@test.local",
        hashed_password=hash_password(STRONG),
    )
    session.add(user)
    await session.flush()
    return user


async def test_login_sets_cookies_and_returns_no_token(session):
    user = await _account(session)
    response = Response()

    body = await login(
        LoginRequest(username=user.username, password=STRONG), response, session
    )

    assert body.model_dump() == {"mfa_required": False, "mfa_token": None}
    assert _cookies(response) == set(AUTH_COOKIES)


async def test_refresh_answers_no_content(session):
    user = await _account(session)
    cookie = f"{REFRESH_TOKEN_COOKIE}={create_refresh_token(str(user.id))}"
    request = Request({"type": "http", "headers": [(b"cookie", cookie.encode())]})
    response = Response()

    assert await refresh_access_token(request, response, session) is None
    assert _cookies(response) == set(AUTH_COOKIES)
    route = next(r for r in router.routes if r.path == "/auth/refresh")
    assert route.status_code == 204
    assert route.response_model is None


def test_account_changes_refuse_another_account():
    other = str(uuid.uuid4())
    with pytest.raises(ValidationError):
        PasswordChangeRequest.model_validate(
            {"user_id": other, "current_password": STRONG, "new_password": STRONG}
        )
    with pytest.raises(ValidationError):
        UsernameChangeRequest.model_validate(
            {"user_id": other, "new_username": "someone"}
        )
