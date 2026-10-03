from __future__ import annotations

import uuid
from datetime import timedelta

import httpx
import jwt
import pyotp
import pytest
from fastapi import FastAPI, HTTPException, Response
from pydantic import ValidationError
from starlette.requests import Request

from app.api.v1 import auth, totp
from app.config import ALGORITHM, settings
from app.core import ratelimit, security
from app.core.body_limit import MAX_AUTH_REQUEST_BYTES, BodySizeLimitMiddleware
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_token,
    decode_token,
    hash_password,
    signing_key,
)
from app.services import totp as totp_service
from app.services.totp import TOTPService
from shared.definitions.auth import (
    OTP_DAILY_KEY,
    OTP_FAILURE_KEY,
    OTP_FAILURE_LIMIT,
)
from shared.models.user import User

pytestmark = pytest.mark.api

PASSWORD = "Vq7#mT9!pLx2@wRz"


class _Pipe:
    def __init__(self, redis: _Redis):
        self.redis = redis
        self.ops: list = []

    def incr(self, key):
        self.ops.append(("incr", key))

    def expire(self, key, seconds, nx=False):  # noqa: ARG002
        self.ops.append(("expire", key))

    async def execute(self):
        out = []
        for op, key in self.ops:
            if op == "incr":
                self.redis.store[key] = str(int(self.redis.store.get(key, 0)) + 1)
                out.append(int(self.redis.store[key]))
            else:
                out.append(True)
        return out


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

    async def ttl(self, key):  # noqa: ARG002
        return 60

    def pipeline(self, **_kwargs):
        return _Pipe(self)


class _Down:
    def __getattr__(self, _name):
        def fail(*_args, **_kwargs):
            msg = "redis is down"
            raise ConnectionError(msg)

        return fail


@pytest.fixture
def redis(monkeypatch):
    fake = _Redis()
    monkeypatch.setattr(ratelimit, "async_client", lambda: fake)
    monkeypatch.setattr(totp_service, "async_client", lambda: fake)
    return fake


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _user(session) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"sec{tag}",
        email=f"sec{tag}@test.local",
        hashed_password=hash_password(PASSWORD),
    )
    session.add(user)
    await session.flush()
    return user


def _from(address: str) -> Request:
    return Request({"type": "http", "headers": [], "client": (address, 1)})


async def _login(session, username: str, password: str, address: str):
    return await auth.login(
        auth.LoginRequest(username=username, password=password),
        _from(address),
        Response(),
        session,
    )


async def _status(coro) -> int:
    try:
        await coro
    except HTTPException as exc:
        return exc.status_code
    return 200


def _refresh_request(token: str) -> Request:
    cookie = f"{auth.REFRESH_TOKEN_COOKIE}={token}".encode()
    return Request({"type": "http", "headers": [(b"cookie", cookie)]})


# ---------- login ----------


@pytest.mark.parametrize(
    ("field", "size"),
    [("username", 51), ("password", 1025)],
)
def test_login_fields_are_bounded(field, size):
    values = {"username": "user", "password": "pw"} | {field: "a" * size}
    with pytest.raises(ValidationError):
        auth.LoginRequest(**values)


async def test_failures_lock_the_account_for_that_address_only(redis, flush_only):
    user = await _user(flush_only)
    for _ in range(auth.LOGIN_FAILURE_LIMIT):
        assert (
            await _status(_login(flush_only, user.username, "wrong", "198.51.100.7"))
            == 401
        )
    assert (
        await _status(_login(flush_only, user.username, PASSWORD, "198.51.100.7"))
        == 429
    )
    assert (
        await _status(_login(flush_only, user.username, PASSWORD, "203.0.113.9")) == 200
    )


async def test_failures_across_accounts_lock_the_address(redis, flush_only):
    for i in range(auth.LOGIN_ADDRESS_LIMIT):
        await _status(_login(flush_only, f"nobody{i}", "wrong", "198.51.100.8"))
    user = await _user(flush_only)
    assert (
        await _status(_login(flush_only, user.username, PASSWORD, "198.51.100.8"))
        == 429
    )


async def test_login_refuses_when_the_limiter_is_down(monkeypatch, flush_only):
    monkeypatch.setattr(ratelimit, "async_client", lambda: _Down())
    user = await _user(flush_only)
    assert (
        await _status(_login(flush_only, user.username, PASSWORD, "198.51.100.9"))
        == 503
    )


# ---------- refresh ----------


async def test_a_rotated_token_works_inside_grace_without_extending_it(
    redis, flush_only
):
    user = await _user(flush_only)
    token = create_token(str(user.id), TOKEN_TYPE_REFRESH, timedelta(days=1))
    jti = decode_token(token)["jti"]

    await auth.refresh_access_token(_refresh_request(token), Response(), flush_only)
    redis.store[f"grace:jti:{jti}"] = "first"
    await auth.refresh_access_token(_refresh_request(token), Response(), flush_only)
    assert redis.store[f"grace:jti:{jti}"] == "first"


async def test_a_rotated_token_after_grace_signs_the_account_out(redis, flush_only):
    user = await _user(flush_only)
    token = create_token(str(user.id), TOKEN_TYPE_REFRESH, timedelta(days=1))
    jti = decode_token(token)["jti"]

    await auth.refresh_access_token(_refresh_request(token), Response(), flush_only)
    del redis.store[f"grace:jti:{jti}"]

    status = await _status(
        auth.refresh_access_token(_refresh_request(token), Response(), flush_only)
    )
    assert status == 401
    assert f"auth:valid-after:{user.id}" in redis.store


# ---------- tokens ----------


def test_sessions_are_not_signed_with_the_encryption_key():
    assert signing_key() != settings.SECRET_KEY


def test_jwt_secret_key_is_used_when_set(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "k" * 64)
    security.signing_key.cache_clear()
    try:
        assert signing_key() == "k" * 64
    finally:
        security.signing_key.cache_clear()


@pytest.mark.parametrize("key", ["", "shared"])
def test_production_refuses_a_missing_or_shared_signing_key(monkeypatch, key):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY if key else "")
    security.signing_key.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            signing_key()
    finally:
        security.signing_key.cache_clear()


def test_a_token_without_an_id_is_refused():
    payload = decode_token(
        create_token(str(uuid.uuid4()), TOKEN_TYPE_REFRESH, timedelta(minutes=5))
    )
    del payload["jti"]
    assert decode_token(jwt.encode(payload, signing_key(), algorithm=ALGORITHM)) is None


# ---------- re-authentication ----------


async def test_a_username_change_needs_the_current_password(redis, flush_only):
    user = await _user(flush_only)
    wrong = auth.UsernameChangeRequest(
        new_username=f"x{user.username}", current_password="wrong-password"
    )
    assert await _status(auth.change_username(wrong, user, flush_only)) == 401

    right = auth.UsernameChangeRequest(
        new_username=f"x{user.username}", current_password=PASSWORD
    )
    await auth.change_username(right, user, flush_only)
    assert user.username.startswith("x")


async def test_two_factor_setup_needs_the_current_password(redis, flush_only):
    user = await _user(flush_only)
    service = TOTPService(flush_only)
    wrong = totp.TwoFactorSetupRequest(current_password="wrong-password")
    assert await _status(totp.setup_2fa(wrong, user, service)) == 401
    assert user.totp_secret_encrypted is None

    right = totp.TwoFactorSetupRequest(current_password=PASSWORD)
    assert "secret" in await totp.setup_2fa(right, user, service)


# ---------- second factor ----------


async def _enrolled(session) -> tuple[User, str]:
    user = await _user(session)
    service = TOTPService(session)
    secret = (await service.start_setup(user))["secret"]
    await service.verify_and_enable(user, pyotp.TOTP(secret).now())
    return user, secret


async def test_code_failures_spend_the_per_user_budget(redis, flush_only):
    user, _ = await _enrolled(flush_only)
    mfa = create_token(str(user.id), totp.TOKEN_TYPE_MFA, timedelta(minutes=5))
    service = TOTPService(flush_only)
    request = totp.TwoFactorLoginRequest(mfa_token=mfa, code="000000")
    for _ in range(OTP_FAILURE_LIMIT):
        await _status(totp.login_2fa(request, Response(), flush_only, service))
    assert redis.store[OTP_DAILY_KEY.format(user_id=user.id)] == str(OTP_FAILURE_LIMIT)
    assert (
        await _status(totp.login_2fa(request, Response(), flush_only, service)) == 429
    )
    assert OTP_FAILURE_KEY.format(user_id=user.id) in redis.store


async def test_the_replay_guard_refuses_when_redis_is_down(
    redis, flush_only, monkeypatch
):
    user, secret = await _enrolled(flush_only)
    monkeypatch.setattr(totp_service, "async_client", lambda: _Down())
    code = pyotp.TOTP(secret).now()
    assert not await TOTPService(flush_only).verify_code(user, code)


async def test_an_enrolment_code_cannot_be_replayed_at_login(redis, flush_only):
    user = await _user(flush_only)
    service = TOTPService(flush_only)
    secret = (await service.start_setup(user))["secret"]
    code = pyotp.TOTP(secret).now()
    await service.verify_and_enable(user, code)
    assert not await service.verify_code(user, code)


# ---------- request size ----------


async def test_an_oversized_auth_body_is_refused():
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)

    @app.post("/api/v1/auth/login")
    async def login() -> dict:
        return {}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        big = await client.post(
            "/api/v1/auth/login", content=b"x" * (MAX_AUTH_REQUEST_BYTES + 1)
        )
        small = await client.post("/api/v1/auth/login", content=b"{}")
    assert big.status_code == 413
    assert small.status_code == 200
