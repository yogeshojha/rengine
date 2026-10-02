from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import jwt
import pyotp
import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api import deps
from app.api.v1 import auth, totp
from app.api.v1.users import update_user
from app.config import ALGORITHM, settings
from app.core import ratelimit
from app.core.security import (
    ISSUED_MS_CLAIM,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_token,
    decode_token,
    hash_password,
)
from app.services.totp import TOTPService
from shared.models.user import User, UserAdminUpdate

pytestmark = pytest.mark.api

OLD = "Vq7#mT9!pLx2@wRz"
NEW = "Hk4$nW8&qZy3^bUe"


class _Redis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None, nx=False):  # noqa: ARG002
        if nx and key in self.store:
            return None
        self.store[key] = str(value)
        return True

    async def exists(self, key):
        return int(key in self.store)

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture
def redis(monkeypatch):
    fake = _Redis()
    monkeypatch.setattr(ratelimit, "async_client", lambda: fake)
    return fake


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _user(session, *, superuser: bool = False) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"auth{tag}",
        email=f"auth{tag}@test.local",
        hashed_password=hash_password(OLD),
        is_superuser=superuser,
    )
    session.add(user)
    await session.flush()
    return user


def _minted_earlier(user: User, token_type: str) -> str:
    payload = decode_token(create_token(str(user.id), token_type, timedelta(days=1)))
    payload["iat"] -= 5
    payload[ISSUED_MS_CLAIM] -= 5000
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _cookie(response: Response, name: str) -> str | None:
    for header in response.headers.getlist("set-cookie"):
        key, _, rest = header.partition("=")
        if key == name:
            return rest.split(";", 1)[0]
    return None


def _refresh_request(token: str) -> Request:
    cookie = f"{auth.REFRESH_TOKEN_COOKIE}={token}".encode()
    return Request({"type": "http", "headers": [(b"cookie", cookie)]})


async def _refused(payload_token: str, session) -> None:
    with pytest.raises(HTTPException) as exc:
        await deps.user_for_payload(decode_token(payload_token), session)
    assert exc.value.status_code == 401


def test_a_token_carries_its_issue_time():
    payload = decode_token(create_access_token(uuid.uuid4()))
    assert isinstance(payload["iat"], int)
    assert isinstance(payload[ISSUED_MS_CLAIM], int)


async def test_a_token_from_the_same_second_as_a_revocation_is_refused(
    redis, flush_only
):
    user = await _user(flush_only)
    token = create_access_token(str(user.id))
    issued = decode_token(token)[ISSUED_MS_CLAIM]
    redis.store[f"auth:valid-after:{user.id}"] = str(issued + 1)
    await _refused(token, flush_only)
    redis.store[f"auth:valid-after:{user.id}"] = str(issued)
    assert (await deps.user_for_payload(decode_token(token), flush_only)).id == user.id


async def test_a_password_change_refuses_every_earlier_token(redis, flush_only):
    user = await _user(flush_only)
    stolen_refresh = _minted_earlier(user, TOKEN_TYPE_REFRESH)
    stolen_access = _minted_earlier(user, TOKEN_TYPE_ACCESS)

    response = Response()
    await auth.change_password(
        auth.PasswordChangeRequest(current_password=OLD, new_password=NEW),
        response=response,
        current_user=user,
        session=flush_only,
    )

    await _refused(stolen_access, flush_only)
    with pytest.raises(HTTPException) as exc:
        await auth.refresh_access_token(
            _refresh_request(stolen_refresh), Response(), flush_only
        )
    assert exc.value.status_code == 401

    reissued = _cookie(response, auth.REFRESH_TOKEN_COOKIE)
    assert await deps.user_for_payload(decode_token(reissued), flush_only) is user
    await auth.refresh_access_token(_refresh_request(reissued), Response(), flush_only)


async def test_enrolling_two_factor_refuses_every_earlier_token(redis, flush_only):
    user = await _user(flush_only)
    stolen = _minted_earlier(user, TOKEN_TYPE_REFRESH)
    service = TOTPService(flush_only)
    setup = await service.start_setup(user)

    response = Response()
    await totp.verify_2fa(
        totp.TwoFactorCodeRequest(code=pyotp.TOTP(setup["secret"]).now()),
        response=response,
        current_user=user,
        service=service,
    )

    await _refused(stolen, flush_only)
    reissued = _cookie(response, auth.ACCESS_TOKEN_COOKIE)
    assert await deps.user_for_payload(decode_token(reissued), flush_only) is user


async def test_a_deactivated_account_loses_its_event_stream(
    redis, flush_only, monkeypatch
):
    admin = await _user(flush_only, superuser=True)
    user = await _user(flush_only)
    token = create_access_token(str(user.id))

    @asynccontextmanager
    async def _same_session():
        yield flush_only

    monkeypatch.setattr(deps, "async_db_session", _same_session)
    assert await deps.token_still_valid(token)

    await update_user(
        user.id, UserAdminUpdate(is_active=False), flush_only, current_user=admin
    )
    assert not await deps.token_still_valid(token)


async def test_login_returns_no_token_in_the_body(redis, flush_only):
    user = await _user(flush_only)
    response = Response()
    body = await auth.login(
        auth.LoginRequest(username=user.username, password=OLD),
        response,
        flush_only,
    )
    assert set(body.model_dump()) == {"mfa_required", "mfa_token"}
    assert _cookie(response, auth.REFRESH_TOKEN_COOKIE)
