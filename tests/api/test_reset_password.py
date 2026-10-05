from __future__ import annotations

import fnmatch
import uuid
from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException

from app import reset_password
from app.api import deps
from app.config import ALGORITHM, settings
from app.core import ratelimit
from app.core.security import (
    ISSUED_MS_CLAIM,
    TOKEN_TYPE_ACCESS,
    create_token,
    decode_token,
    hash_password,
    signing_key,
    verify_password,
)
from shared.definitions.auth import LOGIN_ACCOUNT_KEY, LOGIN_ADDRESS_KEY
from shared.models.user import User

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

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    async def scan_iter(self, match):
        for key in list(self.store):
            if fnmatch.fnmatchcase(key, match):
                yield key


class _DownRedis:
    def __getattr__(self, name):
        raise ConnectionError(name)


@pytest.fixture
def redis(monkeypatch):
    fake = _Redis()
    monkeypatch.setattr(ratelimit, "async_client", lambda: fake)
    return fake


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _user(session, **fields) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"Reset{tag}",
        email=f"reset{tag}@test.local",
        hashed_password=hash_password(OLD),
        **fields,
    )
    session.add(user)
    await session.flush()
    return user


async def _account(session, user: User) -> reset_password.Account:
    return await reset_password.find(session, user.username)


def _minted_earlier(user: User) -> str:
    payload = decode_token(
        create_token(str(user.id), TOKEN_TYPE_ACCESS, timedelta(days=1))
    )
    payload["iat"] -= 5
    payload[ISSUED_MS_CLAIM] -= 5000
    return jwt.encode(payload, signing_key(), algorithm=ALGORITHM)


async def test_a_reset_sets_the_password_and_refuses_every_earlier_token(
    redis, flush_only
):
    user = await _user(flush_only)
    stolen = _minted_earlier(user)

    signed_out = await reset_password.reset(
        flush_only, await _account(flush_only, user), NEW, remove_2fa=False
    )

    assert signed_out
    assert verify_password(NEW, user.hashed_password)
    with pytest.raises(HTTPException) as exc:
        await deps.user_for_payload(decode_token(stolen), flush_only)
    assert exc.value.status_code == 401


async def test_a_reset_clears_the_accounts_failed_logins_alone(redis, flush_only):
    user = await _user(flush_only)
    name = user.username.lower()
    mine = [
        LOGIN_ACCOUNT_KEY.format(username=name, address=address)
        for address in ("203.0.113.7", "2001:db8::1")
    ]
    kept = [
        LOGIN_ACCOUNT_KEY.format(username=f"{name}x", address="203.0.113.7"),
        LOGIN_ADDRESS_KEY.format(address="203.0.113.7"),
    ]
    for key in mine + kept:
        redis.store[key] = "10"

    await reset_password.reset(
        flush_only, await _account(flush_only, user), NEW, remove_2fa=False
    )

    assert not set(mine) & redis.store.keys()
    assert set(kept) <= redis.store.keys()


async def test_two_factor_is_removed_only_when_asked(redis, flush_only):
    kept = await _user(
        flush_only, totp_enabled=True, totp_secret_encrypted="x", totp_backup_codes=[]
    )
    removed = await _user(
        flush_only, totp_enabled=True, totp_secret_encrypted="x", totp_backup_codes=[]
    )

    kept_account = await _account(flush_only, kept)
    await reset_password.reset(flush_only, kept_account, NEW, remove_2fa=False)
    removed_account = await _account(flush_only, removed)
    await reset_password.reset(flush_only, removed_account, NEW, remove_2fa=True)

    assert kept.totp_enabled
    assert kept.totp_secret_encrypted == "x"
    assert not removed.totp_enabled
    assert removed.totp_secret_encrypted is None
    assert removed.totp_backup_codes is None
    assert "Two-factor authentication is on." in reset_password.report(
        kept_account, signed_out=True, remove_2fa=False
    )
    assert "Two-factor authentication removed." in reset_password.report(
        removed_account, signed_out=True, remove_2fa=True
    )


async def test_an_unknown_user_names_the_active_administrators(flush_only):
    active = await _user(flush_only, is_superuser=True)
    inactive = await _user(flush_only, is_superuser=True, is_active=False)
    member = await _user(flush_only)

    with pytest.raises(reset_password.ResetRefusedError) as exc:
        await reset_password.find(flush_only, "nobody-here")

    message = str(exc.value)
    assert message.startswith("No user named nobody-here.\nAdministrators: ")
    assert active.username in message
    assert inactive.username not in message
    assert member.username not in message


@pytest.mark.parametrize("password", ["", "short", "password123456", "Resetuser2026"])
def test_a_weak_password_is_refused(monkeypatch, password):
    monkeypatch.setattr(settings, "DEBUG", False)
    account = reset_password.Account(
        uuid.uuid4(), "Resetuser", "reset@test.local", True, False
    )
    with pytest.raises(reset_password.ResetRefusedError):
        reset_password.checked(password, account)


async def test_redis_down_is_reported_not_claimed(flush_only, monkeypatch):
    monkeypatch.setattr(ratelimit, "async_client", _DownRedis)
    user = await _user(flush_only, is_active=False)
    account = await _account(flush_only, user)

    signed_out = await reset_password.reset(flush_only, account, NEW, remove_2fa=False)
    lines = reset_password.report(account, signed_out=signed_out, remove_2fa=False)

    assert not signed_out
    assert verify_password(NEW, user.hashed_password)
    assert "Sessions signed out." not in lines
    assert any(line.startswith("Sessions not signed out.") for line in lines)
    assert f"{user.username} is disabled. Enable it in Settings, Users." in lines
