"""Per-task effort on OpenAI and Gemini, in one call and in the tool loop."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from shared.definitions.ai import (
    GOOGLE_THINKING_TOKENS,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    AITask,
    Usage,
)
from shared.services.ai import agent, client, ledger
from shared.services.ai.agent import DONE, AgentTool, converse
from shared.services.ai.client import AIError, complete
from shared.services.ai.config import AIConfig

pytestmark = pytest.mark.api

TASK = AITask.RISK_NARRATIVE.value
OPENAI_REPLY = {
    "choices": [{"message": {"content": "ready"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 3},
}
GOOGLE_REPLY = {
    "candidates": [{"content": {"parts": [{"text": "ready"}]}, "finishReason": "STOP"}],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 3,
        "thoughtsTokenCount": 40,
    },
}
TOOL = AgentTool("show_rows", "Show rows.", {"type": "object", "properties": {}})


@pytest.fixture
def book():
    rows: list[ledger.CallRecord] = []
    ledger.register(rows.append)
    yield rows
    ledger.register(None)


def _cfg(provider: str, model: str) -> AIConfig:
    base = "https://router.example/v1" if provider == "openai_compatible" else ""
    return AIConfig(
        provider=provider,
        api_key="k",
        model=model,
        features={"ask": True},
        base_url=base,
        input_per_mtok=1.0,
        output_per_mtok=1.0,
    )


def _provider(monkeypatch, replies: list) -> list[dict]:
    sent: list[dict] = []
    queue = iter(replies)

    def post(url, payload, headers, timeout, *, proxy=None):
        sent.append(json.loads(json.dumps(payload)))
        reply = next(queue)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(client, "post_json", post)
    monkeypatch.setattr(agent, "post_json", post)
    return sent


def _bad_request() -> AIError:
    return client.http_error(400, '{"error": {"message": "Unknown field."}}')


async def _converse(cfg: AIConfig) -> list:
    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        return "ok", True

    return [
        e
        async for e in converse(
            cfg,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[TOOL],
            call_tool=call_tool,
            task=TASK,
            max_rounds=3,
        )
    ]


def _effort(provider: str, payload: dict) -> str | None:
    if provider == "google":
        thinking = payload["generationConfig"].get("thinkingConfig") or {}
        return thinking.get("thinkingLevel")
    return payload.get("reasoning_effort")


CASES = [
    ("openai", "gpt-6.1-sol", TASK_EFFORT[TASK]),
    ("openai", "gpt-4.1", None),
    ("openai_compatible", "gpt-6.1-sol", None),
    ("google", "gemini-3.8-flash", TASK_EFFORT[TASK].upper()),
    ("google", "gemini-2.0-flash", None),
]


def _reply(provider: str) -> dict:
    return GOOGLE_REPLY if provider == "google" else OPENAI_REPLY


@pytest.mark.parametrize(("provider", "model", "expected"), CASES)
def test_complete_sends_effort_only_to_a_reasoning_catalog_model(
    monkeypatch, book, provider, model, expected
):
    sent = _provider(monkeypatch, [_reply(provider)])
    complete(_cfg(provider, model), system="s", prompt="p", task=TASK)
    assert _effort(provider, sent[0]) == expected


@pytest.mark.parametrize(("provider", "model", "expected"), CASES)
async def test_converse_sends_effort_only_to_a_reasoning_catalog_model(
    monkeypatch, book, provider, model, expected
):
    sent = _provider(monkeypatch, [_reply(provider)])
    events = await _converse(_cfg(provider, model))
    assert events[-1].kind == DONE
    assert _effort(provider, sent[0]) == expected


@pytest.mark.parametrize(
    ("provider", "model"), [("openai", "gpt-6.1-sol"), ("google", "gemini-3.8-flash")]
)
def test_complete_asks_again_without_effort_after_a_400(
    monkeypatch, book, provider, model
):
    sent = _provider(monkeypatch, [_bad_request(), _reply(provider)])
    result = complete(_cfg(provider, model), system="s", prompt="p", task=TASK)
    assert result.text == "ready"
    assert [_effort(provider, p) for p in sent][1] is None
    assert _effort(provider, sent[0]) is not None
    assert len(book) == 1
    assert book[-1].ok


@pytest.mark.parametrize(
    ("provider", "model"), [("openai", "gpt-6.1-sol"), ("google", "gemini-3.8-flash")]
)
def test_complete_fails_on_a_second_400(monkeypatch, book, provider, model):
    sent = _provider(monkeypatch, [_bad_request(), _bad_request()])
    with pytest.raises(AIError, match="Provider returned 400"):
        complete(_cfg(provider, model), system="s", prompt="p", task=TASK)
    assert len(sent) == 2
    assert len(book) == 1
    assert not book[-1].ok


def _spent_400() -> AIError:
    body = '{"error": {"message": "Unknown field."}, "usage": {"prompt_tokens": 9}}'
    return client.http_error(400, body)


def test_complete_counts_what_the_rejected_400_used(monkeypatch, book):
    _provider(monkeypatch, [_spent_400(), OPENAI_REPLY])
    result = complete(_cfg("openai", "gpt-6.1-sol"), system="s", prompt="p", task=TASK)
    assert result.usage == Usage(19, 3)
    assert book[-1].usage == Usage(19, 3)


def test_a_second_400_records_what_both_used(monkeypatch, book):
    _provider(monkeypatch, [_spent_400(), _spent_400()])
    with pytest.raises(AIError):
        complete(_cfg("openai", "gpt-6.1-sol"), system="s", prompt="p", task=TASK)
    assert book[-1].usage == Usage(18, 0)


@pytest.mark.parametrize(
    ("provider", "model"), [("openai", "gpt-4.1"), ("google", "gemini-2.0-flash")]
)
def test_a_400_without_effort_is_not_asked_again(monkeypatch, book, provider, model):
    sent = _provider(monkeypatch, [_bad_request(), _reply(provider)])
    with pytest.raises(AIError):
        complete(_cfg(provider, model), system="s", prompt="p", task=TASK)
    assert len(sent) == 1


def test_a_server_error_is_not_asked_again(monkeypatch, book):
    sent = _provider(monkeypatch, [client.http_error(500, ""), _reply("openai")])
    with pytest.raises(AIError):
        complete(_cfg("openai", "gpt-6.1-sol"), system="s", prompt="p", task=TASK)
    assert len(sent) == 1


@pytest.mark.parametrize(
    ("provider", "model"), [("openai", "gpt-6.1-sol"), ("google", "gemini-3.8-flash")]
)
async def test_converse_drops_effort_for_the_rest_of_the_turn_after_a_400(
    monkeypatch, book, provider, model
):
    if provider == "google":
        call = {
            "candidates": [
                {
                    "content": {"parts": [{"functionCall": {"name": "show_rows"}}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 1},
        }
    else:
        call = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [{"id": "1", "function": {"name": "show_rows"}}],
                    }
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }
    sent = _provider(monkeypatch, [_bad_request(), call, _reply(provider)])
    events = await _converse(_cfg(provider, model))
    assert events[-1].kind == DONE
    assert [_effort(provider, p) is None for p in sent] == [False, True, True]
    assert len(book) == 1
    assert book[-1].ok


@pytest.mark.parametrize(
    ("provider", "model"), [("openai", "gpt-6.1-sol"), ("google", "gemini-3.8-flash")]
)
async def test_converse_fails_on_a_second_400(monkeypatch, book, provider, model):
    sent = _provider(monkeypatch, [_bad_request(), _bad_request()])
    with pytest.raises(AIError, match="Provider returned 400"):
        await _converse(_cfg(provider, model))
    assert len(sent) == 2
    assert len(book) == 1
    assert not book[-1].ok


def test_complete_counts_gemini_thoughts_as_output(monkeypatch, book):
    _provider(monkeypatch, [GOOGLE_REPLY])
    result = complete(
        _cfg("google", "gemini-3.8-flash"), system="s", prompt="p", task=TASK
    )
    assert result.usage == Usage(10, 43)
    assert book[-1].usage == Usage(10, 43)


async def test_converse_counts_gemini_thoughts_as_output(monkeypatch, book):
    _provider(monkeypatch, [GOOGLE_REPLY])
    events = await _converse(_cfg("google", "gemini-3.8-flash"))
    assert events[-1].usage == Usage(10, 43)
    assert book[-1].usage == Usage(10, 43)


@pytest.mark.parametrize("tools", [True, False])
async def test_both_gemini_paths_add_the_thinking_allowance(monkeypatch, book, tools):
    sent = _provider(monkeypatch, [GOOGLE_REPLY])
    cfg = _cfg("google", "gemini-3.8-flash")
    if tools:
        await _converse(cfg)
    else:
        complete(cfg, system="s", prompt="p", task=TASK)
    expected = TASK_OUTPUT_TOKENS[TASK] + GOOGLE_THINKING_TOKENS
    assert sent[0]["generationConfig"]["maxOutputTokens"] == expected


def test_anthropic_shares_the_retry_and_drops_thinking_and_effort(monkeypatch, book):
    import anthropic  # noqa: PLC0415

    calls: list[dict] = []
    reply = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text="ready")],
        usage=SimpleNamespace(
            input_tokens=5,
            output_tokens=1,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            inference_geo=None,
        ),
    )

    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise _bad_sdk_request()
        return reply

    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda **_k: SimpleNamespace(messages=SimpleNamespace(create=create)),
    )
    result = complete(
        _cfg("anthropic", "claude-opus-5-5"), system="s", prompt="p", task=TASK
    )
    assert result.text == "ready"
    assert "output_config" in calls[0]
    assert "thinking" in calls[0]
    assert "output_config" not in calls[1]
    assert "thinking" not in calls[1]


def _bad_sdk_request() -> Exception:
    import anthropic  # noqa: PLC0415
    import httpx2  # noqa: PLC0415

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(400, request=request)
    return anthropic.BadRequestError("Unknown field.", response=response, body=None)


def test_complete_keeps_the_cap_for_a_gemini_model_outside_the_catalog(
    monkeypatch, book
):
    sent = _provider(monkeypatch, [GOOGLE_REPLY])
    complete(_cfg("google", "gemini-2.0-flash"), system="s", prompt="p", task=TASK)
    assert sent[0]["generationConfig"] == {"maxOutputTokens": TASK_OUTPUT_TOKENS[TASK]}


async def test_converse_keeps_the_allowance_for_a_gemini_model_outside_the_catalog(
    monkeypatch, book
):
    sent = _provider(monkeypatch, [GOOGLE_REPLY])
    await _converse(_cfg("google", "gemini-2.0-flash"))
    expected = TASK_OUTPUT_TOKENS[TASK] + GOOGLE_THINKING_TOKENS
    assert sent[0]["generationConfig"] == {"maxOutputTokens": expected}
