from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.ai import (
    DEFAULT_MODEL,
    FAST_MODEL,
    MODEL_BY_ID,
    MODELS,
    TASK_EFFORT,
    AITask,
)
from shared.enums.instance import AIProvider
from shared.services.ai import client
from shared.services.ai.config import AIConfig

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/ai.ts")


def _cfg(provider: str, model: str) -> AIConfig:
    return AIConfig(
        provider=provider, api_key="k", model=model, fast_model=model, features={}
    )


def _as_provider(provider: str) -> str:
    # an Azure deployment is named after the OpenAI model it serves
    if provider == AIProvider.AZURE_OPENAI.value:
        return AIProvider.OPENAI.value
    return provider


@pytest.mark.parametrize("table", [DEFAULT_MODEL, FAST_MODEL])
def test_every_default_is_a_listed_model_of_its_provider(table):
    assert set(table) == {p.value for p in AIProvider}
    for provider, model in table.items():
        assert model in MODEL_BY_ID, model
        assert MODEL_BY_ID[model].provider == _as_provider(provider)


def test_every_listed_model_is_priced_once():
    assert len(MODEL_BY_ID) == len(MODELS)
    for spec in MODELS:
        assert spec.input_per_mtok is not None, spec.id
        assert spec.output_per_mtok is not None, spec.id


def test_the_frontend_mirror_offers_the_same_defaults():
    text = MIRROR.read_text()
    offered = dict(
        re.findall(r"value: AIProvider\.(\w+), name: '[^']+', model: '([^']+)'", text)
    )
    assert {AIProvider[k].value: v for k, v in offered.items()} == DEFAULT_MODEL


def test_openai_asks_for_the_task_effort(monkeypatch):
    sent: list[dict] = []

    def fake_post(url, payload, headers, timeout):
        sent.append(dict(payload))
        return {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        }

    monkeypatch.setattr(client, "_post", fake_post)
    result = client.complete(
        _cfg(AIProvider.OPENAI.value, "gpt-6-sol"),
        system="s",
        prompt="p",
        task=AITask.EXECUTIVE_SUMMARY.value,
    )
    assert result.text == "ok"
    assert sent[0]["reasoning_effort"] == TASK_EFFORT[AITask.EXECUTIVE_SUMMARY.value]


def test_openai_drops_an_effort_the_model_rejects(monkeypatch):
    sent: list[dict] = []

    def fake_post(url, payload, headers, timeout):
        sent.append(dict(payload))
        if "reasoning_effort" in payload:
            msg = "Provider returned 400: unsupported parameter"
            raise client.AIBadRequestError(msg)
        return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    monkeypatch.setattr(client, "_post", fake_post)
    result = client.complete(
        _cfg(AIProvider.OPENAI.value, "gpt-6-luna"),
        system="s",
        prompt="p",
        task=AITask.ISSUE_EXPLAINER.value,
    )
    assert result.text == "ok"
    assert len(sent) == 2
    assert "reasoning_effort" not in sent[1]


def test_an_unlisted_openai_model_gets_no_effort(monkeypatch):
    sent: list[dict] = []

    def fake_post(url, payload, headers, timeout):
        sent.append(dict(payload))
        return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    monkeypatch.setattr(client, "_post", fake_post)
    client.complete(
        _cfg(AIProvider.OPENAI.value, "my-azure-deployment"),
        system="s",
        prompt="p",
        task=AITask.ISSUE_EXPLAINER.value,
    )
    assert "reasoning_effort" not in sent[0]


def test_google_sets_the_thinking_level_and_bills_thoughts(monkeypatch):
    sent: list[dict] = []

    def fake_post(url, payload, headers, timeout):
        sent.append(payload["generationConfig"].copy())
        return {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 4,
                "thoughtsTokenCount": 6,
            },
        }

    monkeypatch.setattr(client, "_post", fake_post)
    result = client.complete(
        _cfg(AIProvider.GOOGLE.value, "gemini-3.8-flash"),
        system="s",
        prompt="p",
        task=AITask.REMEDIATION_PLAN.value,
    )
    assert sent[0]["thinkingConfig"] == {
        "thinkingLevel": TASK_EFFORT[AITask.REMEDIATION_PLAN.value]
    }
    assert (result.input_tokens, result.output_tokens) == (10, 10)


def test_google_drops_a_thinking_level_the_model_rejects(monkeypatch):
    sent: list[dict] = []

    def fake_post(url, payload, headers, timeout):
        sent.append(payload["generationConfig"].copy())
        if "thinkingConfig" in payload["generationConfig"]:
            msg = "Provider returned 400: invalid thinking level"
            raise client.AIBadRequestError(msg)
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    monkeypatch.setattr(client, "_post", fake_post)
    result = client.complete(
        _cfg(AIProvider.GOOGLE.value, "gemini-3.5-flash-lite"),
        system="s",
        prompt="p",
        task=AITask.ISSUE_EXPLAINER.value,
    )
    assert result.text == "ok"
    assert "thinkingConfig" not in sent[1]
