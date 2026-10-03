from __future__ import annotations

import uuid

import pytest

from app.core import ratelimit
from channels import stepup
from shared.definitions.auth import (
    OTP_DAILY_KEY,
    OTP_DAILY_LIMIT,
    OTP_FAILURE_KEY,
    OTP_FAILURE_LIMIT,
)
from shared.definitions.channels import OTP_ATTEMPT_LIMIT

CHANNEL = "telegram"


class _Redis:
    def __init__(self):
        self.store: dict[str, int] = {}

    async def get(self, key):
        return self.store.get(key)

    async def ttl(self, _key):
        return 120

    async def delete(self, key):
        self.store.pop(key, None)

    def pipeline(self, transaction=True):  # noqa: ARG002
        return _Pipeline(self)


class _Pipeline:
    def __init__(self, redis: _Redis):
        self.redis, self.keys = redis, []

    def incr(self, key):
        self.keys.append(key)

    def expire(self, *_args, **_kwargs):
        return None

    async def execute(self):
        for key in self.keys:
            self.redis.store[key] = int(self.redis.store.get(key) or 0) + 1


@pytest.fixture
def redis(monkeypatch):
    fake = _Redis()
    monkeypatch.setattr(ratelimit, "async_client", lambda: fake)
    monkeypatch.setattr(stepup, "async_client", lambda: fake)
    return fake


async def test_a_chat_failure_spends_the_user_web_budget(redis):
    user = uuid.uuid4()
    await stepup.note_failure(CHANNEL, "chat-1", user)
    assert redis.store[OTP_FAILURE_KEY.format(user_id=user)] == 1
    assert redis.store[OTP_DAILY_KEY.format(user_id=user)] == 1


async def test_a_new_chat_does_not_reset_the_user_budget(redis):
    user = uuid.uuid4()
    for n in range(OTP_FAILURE_LIMIT):
        await stepup.note_failure(CHANNEL, f"chat-{n}", user)
    assert await stepup.attempts_exhausted(CHANNEL, "chat-new", user) > 0
    assert await stepup.attempts_exhausted(CHANNEL, "chat-new", uuid.uuid4()) == 0


async def test_web_failures_close_the_chat(redis):
    user = uuid.uuid4()
    redis.store[OTP_FAILURE_KEY.format(user_id=user)] = OTP_FAILURE_LIMIT
    assert await stepup.attempts_exhausted(CHANNEL, "chat-1", user) > 0


async def test_the_daily_budget_holds_after_the_window_clears(redis):
    user = uuid.uuid4()
    redis.store[OTP_DAILY_KEY.format(user_id=user)] = OTP_DAILY_LIMIT
    await stepup.clear_failures(CHANNEL, "chat-1", user)
    assert await stepup.attempts_exhausted(CHANNEL, "chat-1", user) > 0


async def test_the_chat_budget_still_applies(redis):
    user = uuid.uuid4()
    redis.store[stepup.ATTEMPT_KEY.format(channel=CHANNEL, external_id="chat-1")] = (
        OTP_ATTEMPT_LIMIT
    )
    assert await stepup.attempts_exhausted(CHANNEL, "chat-1", user) > 0
    assert await stepup.attempts_exhausted(CHANNEL, "chat-2", user) == 0


async def test_success_clears_the_short_budgets(redis):
    user = uuid.uuid4()
    await stepup.note_failure(CHANNEL, "chat-1", user)
    await stepup.clear_failures(CHANNEL, "chat-1", user)
    assert OTP_FAILURE_KEY.format(user_id=user) not in redis.store
    assert stepup.ATTEMPT_KEY.format(channel=CHANNEL, external_id="chat-1") not in (
        redis.store
    )
    assert redis.store[OTP_DAILY_KEY.format(user_id=user)] == 1
