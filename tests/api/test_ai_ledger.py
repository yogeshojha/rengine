"""Every provider call is one ledger row, whoever made it."""

from __future__ import annotations

import uuid

import pytest

from app.services.ai_settings import AiSettingsService
from shared.definitions.ai import TEST_FEATURE, AITask
from shared.models.ai import AiCall
from shared.services.ai import agent, cache, client, ledger
from shared.services.ai.agent import DONE, TEXT, AgentEvent, converse
from shared.services.ai.client import AIError, complete
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api


@pytest.fixture
def book():
    rows: list[ledger.CallRecord] = []
    ledger.register(rows.append)
    yield rows
    ledger.register(None)


def _cfg(provider: str = "anthropic") -> AIConfig:
    return AIConfig(
        provider=provider,
        api_key="k",
        model="claude-opus-5",
        fast_model="claude-haiku-4-5",
        features={"ask": True},
        base_url="https://user:secret@llm.internal/v1"
        if provider != "anthropic"
        else "",
    )


def test_complete_records_success_and_failure(book, monkeypatch):
    monkeypatch.setattr(client, "_anthropic", lambda *_a, **_k: ("fine", (120, 30)))
    with ledger.source("user", uuid.UUID(int=7), uuid.UUID(int=7)):
        result = complete(
            _cfg(), system="s", prompt="p", task=AITask.CONNECTION_TEST.value
        )
    assert result.text == "fine"
    assert len(book) == 1
    rec = book[0]
    assert (rec.task, rec.feature, rec.ok) == (
        AITask.CONNECTION_TEST.value,
        TEST_FEATURE,
        True,
    )
    assert (rec.input_tokens, rec.output_tokens) == (120, 30)
    assert rec.cost_usd is not None
    assert rec.cost_usd > 0
    assert rec.source.kind == "user"
    assert rec.source.user_id == uuid.UUID(int=7)

    def boom(*a, **k):
        msg = "Provider returned 401: bad key at https://api/x?key=abc"
        raise AIError(msg)

    monkeypatch.setattr(client, "_anthropic", boom)
    with pytest.raises(AIError):
        complete(_cfg(), system="s", prompt="p", task=AITask.RISK_NARRATIVE.value)
    assert len(book) == 2
    assert book[1].ok is False
    assert book[1].feature == "report_narrative"
    assert "key=abc" not in (book[1].error or "")


def test_a_cached_narrative_is_a_ledger_row_with_no_cost(book, monkeypatch):
    class Hit:
        content = "cached prose"

    monkeypatch.setattr(cache, "lookup", lambda *_a, **_k: Hit())
    text = cache.narrate(
        None, _cfg(), task=AITask.RISK_NARRATIVE.value, system="s", prompt="p"
    )
    assert text == "cached prose"
    assert len(book) == 1
    assert book[0].cached is True
    assert book[0].cost_usd == 0.0


async def test_narrate_async_records_hits_and_calls_under_the_source(book, monkeypatch):
    class Hit:
        content = "cached prose"

    class Session:
        async def run_sync(self, fn):
            return fn(None)

    task = AITask.RULE_SUGGESTION.value
    monkeypatch.setattr(cache, "lookup", lambda *_a, **_k: Hit())
    text = await cache.narrate_async(
        Session(), _cfg(), task=task, system="s", prompt="p"
    )
    assert text == "cached prose"
    assert book[-1].cached is True

    stored: list[str] = []
    monkeypatch.setattr(cache, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(cache, "store", lambda *_a, **k: stored.append(k["key"]))
    monkeypatch.setattr(client, "_anthropic", lambda *_a, **_k: ("fresh", (10, 5)))
    with ledger.source("scan", uuid.UUID(int=9)):
        text = await cache.narrate_async(
            Session(), _cfg(), task=task, system="s", prompt="p", fast=True
        )
    assert text == "fresh"
    assert len(stored) == 1
    assert (book[-1].cached, book[-1].source.kind) == (False, "scan")


async def test_converse_records_rounds_and_partial_usage_on_failure(book, monkeypatch):
    async def happy(
        cfg, model, system, messages, tools, call_tool, max_tokens, effort, budget
    ):
        yield AgentEvent(TEXT, text="hi")
        yield AgentEvent(
            DONE, input_tokens=900, output_tokens=80, model=model, rounds=2
        )

    monkeypatch.setattr(agent, "_anthropic", happy)

    async def call_tool(name, args):
        return "", True

    with ledger.source("thread", uuid.UUID(int=3), uuid.UUID(int=9)):
        events = [
            e
            async for e in converse(
                _cfg(),
                system="s",
                messages=[{"role": "user", "content": "q"}],
                tools=[],
                call_tool=call_tool,
                task=AITask.ASK.value,
                max_rounds=6,
            )
        ]
    assert events[-1].kind == DONE
    assert len(book) == 1
    assert (book[0].feature, book[0].rounds, book[0].input_tokens) == ("ask", 2, 900)
    assert book[0].source.kind == "thread"

    async def sad(
        cfg, model, system, messages, tools, call_tool, max_tokens, effort, budget
    ):
        yield AgentEvent(TEXT, text="partial")
        msg = "budget"
        raise AIError(msg, input_tokens=400, output_tokens=10)

    monkeypatch.setattr(agent, "_anthropic", sad)
    with pytest.raises(AIError):
        async for _ in converse(
            _cfg(),
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[],
            call_tool=call_tool,
            task=AITask.ASK.value,
            max_rounds=6,
        ):
            pass
    assert len(book) == 2
    assert book[1].ok is False
    assert book[1].input_tokens == 400


def test_a_failure_message_never_carries_credentials(book, monkeypatch):
    def boom(*a, **k):
        msg = "connect to https://user:secret@llm.internal/v1/chat/completions?token=t failed"
        raise AIError(msg)

    monkeypatch.setattr(client, "_openai", boom)
    with pytest.raises(AIError):
        complete(_cfg("openai_compatible"), system="s", prompt="p", task="ask")
    assert "secret" not in (book[0].error or "")
    assert "token=t" not in (book[0].error or "")


def test_a_compatible_provider_with_no_base_url_never_sends_the_key(book, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        client, "post_json", lambda url, *_a, **_k: sent.append(url) or {}
    )
    cfg = AIConfig(
        provider="openai_compatible",
        api_key="k",
        model="m",
        fast_model="m",
        features={},
    )
    with pytest.raises(AIError):
        complete(cfg, system="s", prompt="p", task=AITask.CONNECTION_TEST.value)
    assert sent == []
    assert book[0].ok is False


async def test_usage_is_read_from_the_ledger(estate):
    now = utc_now()
    estate.session.add_all(
        [
            AiCall(
                at=now,
                task="ask",
                feature="ask",
                provider="anthropic",
                model="m",
                input_tokens=100,
                output_tokens=10,
                cost_usd=0.02,
            ),
            AiCall(
                at=now,
                task="ask",
                feature="ask",
                provider="anthropic",
                model="m",
                ok=False,
                error="boom",
            ),
            AiCall(
                at=now,
                task="risk_narrative",
                feature="report_narrative",
                provider="anthropic",
                model="m",
                cached=True,
                cost_usd=0.0,
            ),
            AiCall(
                at=now,
                task="connection_test",
                feature=TEST_FEATURE,
                provider="anthropic",
                model="m",
                input_tokens=5,
                output_tokens=1,
                cost_usd=0.001,
            ),
        ]
    )
    await estate.session.flush()
    usage = await AiSettingsService(estate.session).usage()
    assert usage.calls == 3
    assert usage.failed == 1
    assert usage.cost_usd == pytest.approx(0.021)
    features = {f.feature: f for f in usage.by_feature}
    assert features["ask"].calls == 2
    assert features["ask"].failed == 1
    assert features[TEST_FEATURE].label == "Connection tests"
    assert features["report_narrative"].cached == 1
    recent = await AiSettingsService(estate.session).calls(10)
    assert len(recent) == 4
    assert recent[0].feature in {"ask", "report_narrative", TEST_FEATURE}


def test_unregistered_ledger_does_not_break_a_call(monkeypatch):
    ledger.register(None)
    monkeypatch.setattr(client, "_anthropic", lambda *_a, **_k: ("ok", (1, 1)))
    assert complete(_cfg(), system="s", prompt="p", task="ask").text == "ok"
