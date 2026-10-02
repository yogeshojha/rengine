from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi import FastAPI

from app.config import ALGORITHM, settings
from app.core import throttle
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_MFA,
    TOKEN_TYPE_REFRESH,
    create_token,
)
from app.core.throttle import GlobalRateLimitMiddleware

pytestmark = pytest.mark.api

LIMIT = 3


class _Pipe:
    def __init__(self, store: dict[str, int]):
        self.store = store
        self.key = ""

    def incr(self, key: str) -> None:
        self.key = key

    def expire(self, key: str, seconds: int, nx: bool = False) -> None:
        pass

    async def execute(self) -> list:
        self.store[self.key] = self.store.get(self.key, 0) + 1
        return [self.store[self.key], True]


class _Redis:
    def __init__(self):
        self.store: dict[str, int] = {}

    def pipeline(self, **_kwargs) -> _Pipe:
        return _Pipe(self.store)


@pytest.fixture
def redis(monkeypatch) -> _Redis:
    fake = _Redis()
    monkeypatch.setattr(throttle, "async_client", lambda: fake)
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_PER_MINUTE", LIMIT)
    return fake


def _client() -> httpx.AsyncClient:
    app = FastAPI()
    app.add_middleware(GlobalRateLimitMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("172.19.0.10", 5173)),
        base_url="http://test",
    )


def _token(user: uuid.UUID, kind: str = TOKEN_TYPE_ACCESS) -> str:
    return create_token(str(user), kind, timedelta(minutes=5))


async def _statuses(n: int, **kwargs) -> list[int]:
    async with _client() as client:
        return [(await client.get("/ping", **kwargs)).status_code for _ in range(n)]


def _cookie(token: str) -> dict:
    return {"headers": {"cookie": f"{ACCESS_TOKEN_COOKIE}={token}"}}


def _bearer(token: str) -> dict:
    return {"headers": {"authorization": f"Bearer {token}"}}


async def test_signed_in_users_behind_one_address_have_their_own_budget(redis):
    first, second = uuid.uuid4(), uuid.uuid4()
    assert await _statuses(LIMIT + 1, **_cookie(_token(first))) == [200] * LIMIT + [429]
    assert await _statuses(1, **_cookie(_token(second))) == [200]
    assert await _statuses(1, **_bearer(_token(second))) == [200]
    assert f"throttle:user:{first}" in next(iter(redis.store))


async def test_a_bearer_token_shares_the_budget_of_its_user(redis):
    user = uuid.uuid4()
    assert await _statuses(LIMIT, **_bearer(_token(user))) == [200] * LIMIT
    assert await _statuses(1, **_cookie(_token(user))) == [429]


async def test_anonymous_requests_share_the_client_address(redis):
    assert await _statuses(LIMIT + 1) == [200] * LIMIT + [429]
    assert next(iter(redis.store)).startswith("throttle:ip:172.19.0.10:")


async def test_a_forwarded_header_does_not_move_the_budget(redis):
    async with _client() as client:
        codes = [
            (
                await client.get("/ping", headers={"x-forwarded-for": f"10.0.0.{i}"})
            ).status_code
            for i in range(LIMIT + 1)
        ]
    assert codes == [200] * LIMIT + [429]
    assert len(redis.store) == 1


@pytest.mark.parametrize("kind", [TOKEN_TYPE_REFRESH, TOKEN_TYPE_MFA])
async def test_a_token_that_is_not_an_access_token_counts_as_the_address(redis, kind):
    await _statuses(1, **_bearer(_token(uuid.uuid4(), kind)))
    assert next(iter(redis.store)).startswith("throttle:ip:")


async def test_a_forged_or_expired_token_counts_as_the_address(redis):
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": TOKEN_TYPE_ACCESS,
            "exp": now + timedelta(minutes=5),
        },
        "not-the-secret-this-instance-signs-with",
        algorithm=ALGORITHM,
    )
    expired = create_token(str(uuid.uuid4()), TOKEN_TYPE_ACCESS, timedelta(seconds=-60))
    await _statuses(1, **_bearer(forged))
    await _statuses(1, **_cookie(expired))
    await _statuses(1, **_bearer("rng_service_token"))
    assert len(redis.store) == 1
    assert next(iter(redis.store)).startswith("throttle:ip:")


async def test_the_limiter_fails_open_when_redis_is_down(monkeypatch):
    def down():
        raise ConnectionError

    monkeypatch.setattr(throttle, "async_client", down)
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_PER_MINUTE", 1)
    assert await _statuses(3) == [200, 200, 200]
