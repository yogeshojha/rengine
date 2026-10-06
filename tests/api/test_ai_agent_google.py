"""Gemini function calling through the shared agent loop."""

from __future__ import annotations

import pytest

from app.services.ask import tools as ask_tools
from app.services.ask.estate.service import agent_tools as estate_tools
from shared.services.ai import agent
from shared.services.ai.agent import CALL, DONE, RESULT, TEXT, AgentTool, converse
from shared.services.ai.client import DECLINED, AIError
from shared.services.ai.config import AIConfig

pytestmark = pytest.mark.api

SCHEMA = {
    "title": "Input",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "title": "Title", "default": None},
        "target": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "default": None,
            "title": "Target",
            "description": "A target.",
        },
        "ids": {"type": "array", "items": {"type": "string", "title": "Id"}},
    },
    "required": [],
}


def test_schema_keeps_property_names_and_drops_what_gemini_refuses():
    out = agent.google_schema(SCHEMA)
    assert set(out["properties"]) == {"title", "target", "ids"}
    assert "additionalProperties" not in out
    assert "title" not in out
    assert out["properties"]["target"] == {
        "type": "string",
        "description": "A target.",
        "nullable": True,
    }
    assert out["properties"]["ids"]["items"] == {"type": "string"}


def test_a_tool_without_arguments_declares_none():
    tool = AgentTool("ping", "Ping.", {"type": "object", "properties": {}})
    assert agent._declaration(tool) == {"name": "ping", "description": "Ping."}


async def test_gemini_calls_a_tool_then_answers(monkeypatch):
    sent: list[dict] = []
    bodies = iter(
        [
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {"text": "Looking. "},
                                {
                                    "functionCall": {
                                        "name": "show_rows",
                                        "args": {"dimension": "web_assets"},
                                    }
                                },
                            ],
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4},
            },
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": "9 rows [B1]."}],
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 6},
            },
        ]
    )

    def post(url, payload, headers, timeout, *, proxy=None):
        sent.append(payload)
        return next(bodies)

    monkeypatch.setattr(agent, "post_json", post)
    monkeypatch.setattr(agent.ledger, "record", lambda _record: None)

    calls: list[tuple[str, dict]] = []

    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        calls.append((name, args))
        return "B1: 9 web assets", True

    cfg = AIConfig(
        provider="google", api_key="k", model="gemini-2.5-pro", features={"ask": True}
    )
    tool = AgentTool("show_rows", "Show rows.", SCHEMA)
    events = [
        e
        async for e in converse(
            cfg,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[tool],
            call_tool=call_tool,
            task="ask",
            max_rounds=3,
        )
    ]
    kinds = [e.kind for e in events]
    assert kinds == [TEXT, CALL, RESULT, TEXT, TEXT, DONE]
    assert calls == [("show_rows", {"dimension": "web_assets"})]
    assert sent[0]["tools"][0]["functionDeclarations"][0]["name"] == "show_rows"
    reply = sent[1]["contents"][-1]
    assert reply["role"] == "user"
    assert reply["parts"][0]["functionResponse"]["response"]["content"] == (
        "B1: 9 web assets"
    )
    assert events[-1].usage.input_tokens == 40


def _round(parts, finish="STOP", usage=None):
    return {
        "candidates": [
            {"content": {"role": "model", "parts": parts}, "finishReason": finish}
        ],
        "usageMetadata": usage or {"promptTokenCount": 1, "candidatesTokenCount": 1},
    }


async def _run(monkeypatch, bodies):
    sent: list[dict] = []
    queue = iter(bodies)

    def post(url, payload, headers, timeout, *, proxy=None):
        sent.append(payload)
        return next(queue)

    monkeypatch.setattr(agent, "post_json", post)
    monkeypatch.setattr(agent.ledger, "record", lambda _record: None)

    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        return "ok", True

    cfg = AIConfig(
        provider="google", api_key="k", model="gemini-2.5-pro", features={"ask": True}
    )
    events = [
        e
        async for e in converse(
            cfg,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[AgentTool("show_rows", "Show rows.", SCHEMA)],
            call_tool=call_tool,
            task="ask",
            max_rounds=3,
        )
    ]
    return events, sent


CALL_PART = {
    "functionCall": {"name": "show_rows", "args": {}},
    "thoughtSignature": "sig-1",
}


async def test_a_thought_signature_goes_back_unchanged(monkeypatch):
    _, sent = await _run(
        monkeypatch, [_round([CALL_PART]), _round([{"text": "done [B1]."}])]
    )
    assert sent[1]["contents"][-2]["parts"][0]["thoughtSignature"] == "sig-1"
    assert sent[0]["generationConfig"]["maxOutputTokens"] > 4000


async def test_a_malformed_call_is_not_an_answer(monkeypatch):
    with pytest.raises(AIError) as stopped:
        await _run(monkeypatch, [_round([], finish="MALFORMED_FUNCTION_CALL")])
    assert "MALFORMED_FUNCTION_CALL" in str(stopped.value)


async def test_safety_after_narration_is_declined(monkeypatch):
    with pytest.raises(AIError) as declined:
        await _run(
            monkeypatch,
            [_round([{"text": "Looking. "}, CALL_PART]), _round([], finish="SAFETY")],
        )
    assert str(declined.value) == DECLINED


async def test_out_of_tokens_with_no_text(monkeypatch):
    with pytest.raises(AIError) as cut:
        await _run(monkeypatch, [_round([], finish="MAX_TOKENS")])
    assert str(cut.value) == agent.OUT_OF_BUDGET


async def test_a_blocked_prompt_is_declined(monkeypatch):
    with pytest.raises(AIError) as declined:
        await _run(monkeypatch, [{"promptFeedback": {"blockReason": "SAFETY"}}])
    assert str(declined.value) == DECLINED


ALLOWED = frozenset(
    {
        "type",
        "properties",
        "required",
        "description",
        "items",
        "enum",
        "nullable",
        "format",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
        "anyOf",
    }
)


def _keys(schema, path="") -> list[str]:
    bad: list[str] = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "properties":
                for name, sub in value.items():
                    bad += _keys(sub, f"{path}.{name}")
                continue
            if key not in ALLOWED:
                bad.append(f"{path}:{key}")
            if key in ("items", "anyOf"):
                bad += _keys(value, f"{path}.{key}")
    elif isinstance(schema, list):
        for item in schema:
            bad += _keys(item, path)
    return bad


def test_every_ask_tool_fits_gemini():
    for tool in [*ask_tools.agent_tools(), *estate_tools()]:
        assert _keys(agent.google_schema(tool.schema)) == [], tool.name
