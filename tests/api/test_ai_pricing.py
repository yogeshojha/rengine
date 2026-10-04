"""What an AI call cost: usage as billed, one price function, rates kept current."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import delete, select, text

from app.services import ai_settings
from app.services.ai_settings import AiSettingsService
from app.services.datasets import DatasetService
from shared.definitions.ai import (
    BILLED_REFUSALS,
    OPENAI_CHAT_ID,
    UNREPORTED,
    AITask,
    CostSource,
    Rates,
    Usage,
    curated_rates,
    model_alias,
    model_spec,
    openai_chat_model,
    price,
    same_model,
    us_premium,
)
from shared.definitions.datasets import DatasetKind
from shared.definitions.threat_intel import FeedStatus
from shared.models.ai import (
    AiCall,
    AiConnection,
    AiConnectionCreate,
    AiConnectionUpdate,
    AiPrice,
)
from shared.models.threat_intel import ThreatFeed
from shared.services import locks
from shared.services.ai import agent, cache, client, ledger, prices, rates
from shared.services.ai.agent import DONE, STOPPED, TEXT, converse
from shared.services.ai.client import (
    DECLINED,
    AIError,
    AIUsage,
    anthropic_usage,
    complete,
    google_usage,
    list_models,
    openai_usage,
)
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api

OPUS = Rates(4.0, 20.0, 0.2, 5.0)
REAL_DOWNLOAD = prices.download
OPENROUTER = "https://openrouter.ai/api/v1"


@pytest.fixture
def book():
    rows: list[ledger.CallRecord] = []
    ledger.register(rows.append)
    yield rows
    ledger.register(None)


def _cfg(provider: str = "anthropic", model: str = "claude-opus-5-5", **kw) -> AIConfig:
    base = "https://router.example/v1" if provider == "openai_compatible" else ""
    return AIConfig(
        provider=provider,
        api_key="k",
        model=model,
        features={"ask": True},
        base_url=kw.pop("base_url", base),
        **kw,
    )


CATALOG = {
    "data": [
        {
            "id": "anthropic/claude-opus-5.5",
            "pricing": {
                "prompt": "0.000004",
                "completion": "0.00002",
                "input_cache_read": "0.0000002",
                "input_cache_write": "0.000005",
            },
        },
        {
            "id": "openai/gpt-5.5",
            "pricing": {
                "prompt": "0.000005",
                "completion": "0.00003",
                "input_cache_read": "0.0000005",
            },
        },
        {
            "id": "openai/gpt-oss-120b",
            "pricing": {"prompt": "0.000000037", "completion": "0.00000017"},
        },
        {
            "id": "google/gemini-3.8-flash",
            "pricing": {
                "prompt": "0.00000075",
                "completion": "0.00000375",
                "input_cache_read": "0.000000075",
            },
        },
        {
            "id": "z-ai/glm-5.3",
            "pricing": {
                "prompt": "0.0000014",
                "completion": "0.0000044",
                "input_cache_read": "0.00000014",
            },
        },
        {"id": "openrouter/auto", "pricing": {"prompt": "-1", "completion": "-1"}},
        {"id": "vendor/free", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "vendor/half", "pricing": {"prompt": "0.000001"}},
        {"id": "vendor/odd", "pricing": "n/a"},
        {"id": "v/" + "x" * 200, "pricing": {"prompt": "0", "completion": "0"}},
        "not a row",
    ]
}
BODY = json.dumps(CATALOG).encode()
LISTED = len(prices.parse(CATALOG))


def _seed(cache_) -> None:
    cache_.set(prices.CACHE_KEY, prices._encode(prices.parse(CATALOG)))


def _usage(inp: int, out: int, reads: int = 0, writes: int = 0, geo: str | None = None):
    return SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=reads,
        cache_creation_input_tokens=writes,
        inference_geo=geo,
    )


def _text(value: str):
    return SimpleNamespace(type="text", text=value)


def _anthropic_reply(monkeypatch, create) -> None:
    import anthropic  # noqa: PLC0415

    fake = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(anthropic, "Anthropic", lambda **_k: fake)


def _http_request():
    import httpx2  # noqa: PLC0415

    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


# ---------- the price function ----------


def test_a_reported_cost_wins_over_every_rate():
    usage = Usage(1000, 100, reported_cost=0.0123)
    assert price(usage, OPUS, "anthropic") == price(usage, None, "openai")
    charge = price(usage, OPUS, "anthropic")
    assert (charge.usd, charge.source, charge.rates) == (0.0123, "provider", None)
    assert price(Usage(10, 1, reported_cost=0.0), None, "x").usd == 0.0


def test_a_call_reported_with_no_tokens_costs_nothing_whatever_the_model():
    for rates_ in (None, OPUS):
        charge = price(Usage(), rates_, "anthropic")
        assert (charge.usd, charge.source) == (0.0, None)


def test_a_call_whose_usage_never_came_back_is_unpriced_not_free():
    assert price(UNREPORTED, OPUS, "anthropic").usd is None
    spent = Usage(1000, 40, reported_cost=0.002) + UNREPORTED
    assert (spent.input_tokens, spent.reported, spent.reported_cost) == (
        1000,
        False,
        None,
    )
    assert price(spent, OPUS, "anthropic").usd is None


def test_a_free_server_costs_nothing_even_unreported():
    for usage in (UNREPORTED, Usage(10_000, 2_000)):
        charge = price(usage, Rates(0.0, 0.0), "openai_compatible")
        assert (charge.usd, charge.source) == (0.0, CostSource.LIST.value)
    assert not Rates(0.0, 0.0, 0.1).free


def test_tokens_with_no_rate_are_unpriced():
    charge = price(Usage(10, 1), None, "anthropic")
    assert (charge.usd, charge.source) == (None, None)


def test_list_maths_prices_each_kind_of_token_at_its_rate():
    usage = Usage(10_000, 1_000, cache_read_tokens=6_000, cache_write_tokens=2_000)
    charge = price(usage, OPUS, "anthropic")
    expected = (2_000 * 4.0 + 6_000 * 0.2 + 2_000 * 5.0 + 1_000 * 20.0) / 1e6
    assert charge.usd == pytest.approx(expected)
    assert (charge.source, charge.rates) == (CostSource.LIST.value, OPUS)


def test_a_missing_cache_rate_falls_back_by_provider():
    usage = Usage(10_000, 0, cache_read_tokens=4_000, cache_write_tokens=1_000)
    bare = Rates(2.0, 10.0)
    anthropic = (5_000 * 2.0 + 4_000 * 2.0 + 1_000 * 2.5) / 1e6
    elsewhere = (5_000 * 2.0 + 4_000 * 2.0 + 1_000 * 2.0) / 1e6
    assert price(usage, bare, "anthropic").usd == pytest.approx(anthropic)
    assert price(usage, bare, "openai").usd == pytest.approx(elsewhere)


def test_cached_tokens_never_count_twice():
    usage = Usage(100, 0, cache_read_tokens=150)
    assert price(usage, OPUS, "anthropic").usd == pytest.approx(150 * 0.2 / 1e6)


def test_usage_adds_up_and_keeps_a_reported_cost_only_when_every_part_has_one():
    a = Usage(100, 10, 50, 0, 0.01)
    b = Usage(200, 20, 0, 30, 0.02)
    total = a + b
    assert (total.input_tokens, total.output_tokens) == (300, 30)
    assert (total.cache_read_tokens, total.cache_write_tokens) == (50, 30)
    assert total.reported_cost == pytest.approx(0.03)
    assert (a + Usage(5, 5)).reported_cost is None
    assert (Usage() + a).reported_cost == 0.01
    assert (Usage() + a).billable is None


# ---------- refusals ----------


def _refusal(category: str | None, content=(), out: int = 0):
    return SimpleNamespace(
        stop_reason="refusal",
        stop_details=SimpleNamespace(category=category),
        content=list(content),
        usage=_usage(9_000, out),
    )


@pytest.mark.parametrize("category", ["cyber", "general_harms", None])
def test_a_refusal_before_any_output_is_free_outside_the_billed_categories(
    book, monkeypatch, category
):
    _anthropic_reply(monkeypatch, lambda **_k: _refusal(category))
    with pytest.raises(AIError, match=DECLINED):
        complete(_cfg(), system="s", prompt="p", task="ask")
    row = ledger.row_values(book[-1])
    assert (row["ok"], row["input_tokens"], row["cost_usd"]) == (False, 9_000, 0.0)


@pytest.mark.parametrize("category", sorted(BILLED_REFUSALS))
def test_a_refusal_before_any_output_is_billed_in_the_billed_categories(
    book, monkeypatch, category
):
    _anthropic_reply(monkeypatch, lambda **_k: _refusal(category))
    with pytest.raises(AIError):
        complete(_cfg(), system="s", prompt="p", task="ask")
    assert book[-1].priced().usd == pytest.approx(9_000 * 4.0 / 1e6)


def test_a_refusal_after_output_is_billed_whatever_its_category(book, monkeypatch):
    partial = _refusal("cyber", [_text("Part")], out=40)
    _anthropic_reply(monkeypatch, lambda **_k: partial)
    with pytest.raises(AIError):
        complete(_cfg(), system="s", prompt="p", task="ask")
    assert book[-1].priced().usd == pytest.approx((9_000 * 4.0 + 40 * 20.0) / 1e6)


# ---------- US-only inference ----------


@pytest.mark.parametrize(
    ("model", "premium"),
    [
        ("claude-opus-5-5", True),
        ("claude-sonnet-5-5", True),
        ("claude-fable-5-1", True),
        ("claude-opus-5", True),
        ("claude-opus-4-6", True),
        ("claude-opus-4-6-20260205", True),
        ("claude-haiku-4-5", False),
        ("claude-haiku-4-5-20251001", False),
        ("claude-sonnet-4-5-20250929", False),
        ("claude-opus-4-1", False),
        ("claude-3-7-sonnet-20250219", False),
        ("gpt-6.1-sol", False),
    ],
)
def test_the_us_premium_starts_at_claude_4_6(model, premium):
    assert us_premium(model) is premium


def test_us_only_inference_costs_a_tenth_more_on_every_rate():
    raw = _usage(9_000, 500, reads=1_000, writes=200, geo="us")
    usage = anthropic_usage(raw, "claude-opus-5-5")
    assert usage.counts == (10_200, 500, 1_000, 200)
    listed = (9_000 * 4.0 + 1_000 * 0.2 + 200 * 5.0 + 500 * 20.0) / 1e6
    assert price(usage, OPUS, "anthropic").usd == pytest.approx(listed * 1.1)
    assert anthropic_usage(raw, "claude-haiku-4-5").billable is None
    assert anthropic_usage(
        _usage(9_000, 500, geo="global"), "claude-opus-5-5"
    ) == Usage(9_000, 500)


def test_us_only_inference_reaches_the_ledger(book, monkeypatch):
    reply = SimpleNamespace(
        stop_reason="end_turn",
        content=[_text("ready")],
        usage=_usage(2_000, 100, geo="us"),
    )
    _anthropic_reply(monkeypatch, lambda **_k: reply)
    result = complete(
        _cfg(model="claude-sonnet-5-5"), system="s", prompt="p", task="ask"
    )
    expected = (2_000 * 2.0 + 100 * 10.0) * 1.1 / 1e6
    assert result.charge.usd == pytest.approx(expected)
    assert book[-1].priced().usd == pytest.approx(expected)


# ---------- usage as each provider bills it ----------


def test_anthropic_cache_tokens_are_added_to_the_input():
    assert anthropic_usage(_usage(100, 20, 900, 50)) == Usage(1050, 20, 900, 50)
    bare = SimpleNamespace(
        input_tokens=7,
        output_tokens=1,
        cache_read_input_tokens=None,
        cache_creation_input_tokens=None,
    )
    assert anthropic_usage(bare) == Usage(7, 1)
    assert anthropic_usage(None) == UNREPORTED


def test_openai_cached_tokens_sit_inside_the_prompt():
    raw = {
        "prompt_tokens": 2000,
        "completion_tokens": 300,
        "prompt_tokens_details": {"cached_tokens": 1536, "cache_write_tokens": 100},
        "completion_tokens_details": {"reasoning_tokens": 250},
    }
    assert openai_usage(raw) == Usage(2000, 300, 1536, 100)
    assert openai_usage(None) == UNREPORTED


@pytest.mark.parametrize(
    ("cost", "reported"),
    [
        (0.00042, 0.00042),
        ("0.00042", 0.00042),
        ("-1", None),
        (float("inf"), None),
        ("nan", None),
        (True, None),
        (None, None),
    ],
)
def test_a_router_cost_is_read_as_a_number_or_a_numeric_string(cost, reported):
    usage = openai_usage({"prompt_tokens": 10, "completion_tokens": 2, "cost": cost})
    assert usage.reported_cost == (
        pytest.approx(reported) if reported is not None else None
    )


def test_a_byok_cost_adds_the_upstream_charge():
    raw = {
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "cost": 0.95,
        "is_byok": True,
        "cost_details": {"upstream_inference_cost": 19},
    }
    assert openai_usage(raw).reported_cost == pytest.approx(19.95)
    raw["is_byok"] = False
    assert openai_usage(raw).reported_cost == pytest.approx(0.95)


def test_google_thoughts_are_output_and_cached_content_is_input():
    raw = {
        "promptTokenCount": 1000,
        "candidatesTokenCount": 50,
        "thoughtsTokenCount": 300,
        "cachedContentTokenCount": 400,
        "totalTokenCount": 1350,
    }
    usage = google_usage(raw)
    assert usage == Usage(1000, 350, 400)
    flash = curated_rates("gemini-3.8-flash")
    expected = (600 * 0.75 + 400 * 0.075 + 350 * 3.75) / 1e6
    assert price(usage, flash, "google").usd == pytest.approx(expected)
    assert google_usage(None) == UNREPORTED


def test_google_complete_records_thoughts_and_cache(book, monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": "ready"}]}}],
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 50,
            "thoughtsTokenCount": 300,
            "cachedContentTokenCount": 400,
        },
    }
    monkeypatch.setattr(client, "post_json", lambda *_a, **_k: body)
    result = complete(
        _cfg("google", "gemini-3.8-flash"), system="s", prompt="p", task="ask"
    )
    assert result.usage == Usage(1000, 350, 400)
    assert book[-1].usage == Usage(1000, 350, 400)
    assert book[-1].priced().usd == pytest.approx(result.charge.usd)


def test_anthropic_complete_records_cache_reads_and_writes(book, monkeypatch):
    reply = SimpleNamespace(
        stop_reason="end_turn", content=[_text("ready")], usage=_usage(100, 20, 900, 50)
    )
    _anthropic_reply(monkeypatch, lambda **_k: reply)
    complete(_cfg(model="claude-haiku-4-5"), system="s", prompt="p", task="ask")

    row = ledger.row_values(book[-1])
    assert (row["input_tokens"], row["output_tokens"]) == (1050, 20)
    assert (row["cache_read_tokens"], row["cache_write_tokens"]) == (900, 50)
    expected = (100 * 1.0 + 900 * 0.1 + 50 * 1.25 + 20 * 5.0) / 1e6
    assert row["cost_usd"] == pytest.approx(expected)
    assert (row["cost_source"], row["input_per_mtok"], row["output_per_mtok"]) == (
        "list",
        1.0,
        5.0,
    )


def test_a_provider_cost_is_stored_as_reported(book, monkeypatch):
    body = {
        "choices": [{"message": {"content": "ready"}}],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 3,
            "cost": "0.0000431",
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }
    monkeypatch.setattr(client, "post_json", lambda *_a, **_k: body)
    routed = _cfg(
        "openai_compatible",
        "z-ai/glm-5.3",
        input_per_mtok=1.26,
        output_per_mtok=3.96,
    )
    complete(routed, system="s", prompt="p", task="connection_test")
    row = ledger.row_values(book[-1])
    assert (row["cost_usd"], row["cost_source"]) == (0.0000431, "provider")
    assert (row["input_per_mtok"], row["output_per_mtok"]) == (None, None)


# ---------- failures: what reached the server ----------


def test_an_error_body_with_usage_is_kept(book, monkeypatch):
    def refuse(*_a, **_k):
        raise client.http_error(
            502,
            json.dumps(
                {
                    "error": {"message": "upstream"},
                    "usage": {"prompt_tokens": 40, "completion_tokens": 0},
                }
            ),
        )

    monkeypatch.setattr(client, "post_json", refuse)
    with pytest.raises(AIError):
        complete(_cfg("openai", "gpt-6.1-sol"), system="s", prompt="p", task="ask")
    assert book[-1].usage == Usage(40, 0)
    assert book[-1].priced().usd == pytest.approx(40 * 2.0 / 1e6)


@pytest.mark.parametrize(
    ("status", "body", "reported"),
    [
        (401, '{"error": {"message": "bad key"}}', True),
        (429, "", True),
        (500, "", True),
        (529, '{"type": "error", "error": {"type": "overloaded_error"}}', True),
        (504, "", False),
        (524, "<html>timeout</html>", False),
    ],
)
def test_an_error_status_is_free_unless_a_gateway_timed_out(status, body, reported):
    spent = client.http_error(status, body).usage
    assert spent.reported is reported
    assert price(spent, Rates(2.0, 10.0), "openai").usd == (0.0 if reported else None)


@pytest.mark.parametrize(
    ("error", "reported"),
    [
        (httpx.ConnectError("refused"), True),
        (httpx.ConnectTimeout("slow"), True),
        (httpx.ReadTimeout("timed out"), False),
        (httpx.RemoteProtocolError("dropped"), False),
        (httpx.ReadError("reset"), False),
    ],
)
def test_a_transport_failure_is_unknown_once_the_request_left(
    monkeypatch, error, reported
):
    def fail(*_a, **_k):
        raise error

    monkeypatch.setattr(httpx.Client, "post", fail)
    with pytest.raises(AIError) as err:
        client.post_json("https://router.example/v1/chat/completions", {}, {}, 1.0)
    assert err.value.usage.reported is reported


def test_a_timed_out_call_is_unpriced_and_a_rejected_one_is_free(book, monkeypatch):
    def timed_out(*_a, **_k):
        msg = "timed out"
        raise httpx.ReadTimeout(msg)

    routed = _cfg(
        "openai_compatible", "z-ai/glm-5.3", input_per_mtok=1.26, output_per_mtok=3.96
    )
    monkeypatch.setattr(httpx.Client, "post", timed_out)
    with pytest.raises(AIError):
        complete(routed, system="s", prompt="p", task="ask")
    timed = ledger.row_values(book[-1])
    assert (timed["ok"], timed["cost_usd"], timed["cost_source"]) == (False, None, None)

    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda *_a, **_k: httpx.Response(401, json={"error": {"message": "bad key"}}),
    )
    with pytest.raises(AIError):
        complete(routed, system="s", prompt="p", task="ask")
    assert ledger.row_values(book[-1])["cost_usd"] == 0.0


def test_an_answer_without_usage_is_unpriced(book, monkeypatch):
    body = {"choices": [{"message": {"content": "ready"}}]}
    monkeypatch.setattr(client, "post_json", lambda *_a, **_k: body)
    complete(_cfg("openai", "gpt-6.1-sol"), system="s", prompt="p", task="ask")
    row = ledger.row_values(book[-1])
    assert (row["ok"], row["input_tokens"], row["cost_usd"]) == (True, 0, None)


@pytest.mark.parametrize(("refused", "cost"), [(True, 0.0), (False, None)])
def test_an_sdk_failure_is_free_only_when_the_request_never_left(
    book, monkeypatch, refused, cost
):
    import anthropic  # noqa: PLC0415
    import httpx2  # noqa: PLC0415

    def create(**_k):
        try:
            if refused:
                reason = "refused"
                raise httpx2.ConnectError(reason)
            reason = "timed out"
            raise httpx2.ReadTimeout(reason)
        except httpx2.TimeoutException as exc:
            raise anthropic.APITimeoutError(request=_http_request()) from exc
        except httpx2.HTTPError as exc:
            raise anthropic.APIConnectionError(request=_http_request()) from exc

    _anthropic_reply(monkeypatch, create)
    with pytest.raises(AIError):
        complete(_cfg(), system="s", prompt="p", task="ask")
    assert ledger.row_values(book[-1])["cost_usd"] == cost


# ---------- snapshots and rate precedence ----------


def test_both_snapshot_spellings_fold_onto_the_alias():
    assert model_alias("claude-haiku-4-5-20251001") == "claude-haiku-4-5"
    assert model_alias("gpt-6.1-sol-2026-09-29") == "gpt-6.1-sol"
    assert model_alias("gemini-2.5-pro-preview-06-05") == "gemini-2.5-pro-preview-06-05"
    assert same_model("gpt-6.1-sol", "gpt-6.1-sol-2026-09-29")
    assert not same_model("gpt-6.1-sol", "gpt-6-sol")
    assert model_spec("gpt-6.1-sol-2026-09-29").label == "GPT-6.1 Sol"
    assert curated_rates("claude-opus-5-5-20261001") == OPUS


def test_the_connection_price_covers_its_model_and_its_snapshots():
    cfg = _cfg(
        "openai_compatible",
        "claude-opus-5",
        input_per_mtok=6.0,
        output_per_mtok=30.0,
    )
    assert cfg.rates("claude-opus-5") == Rates(6.0, 30.0)
    assert cfg.rates("claude-opus-5-20260101") == Rates(6.0, 30.0)
    assert cfg.rates("claude-sonnet-5") == curated_rates("claude-sonnet-5")
    dated = _cfg("openai", "gpt-6.1-sol-2026-09-29")
    assert dated.rates("gpt-6.1-sol-2026-09-29") == curated_rates("gpt-6.1-sol")


def test_the_live_catalog_prices_what_nothing_else_does(price_cache):
    cfg = _cfg("openai", "gpt-5.5")
    assert cfg.rates("gpt-5.5") is None
    _seed(price_cache)
    prices.forget()
    assert cfg.rates("gpt-5.5") == Rates(5.0, 30.0, 0.5, None)
    assert cfg.charge(Usage(1_000_000, 0)).usd == pytest.approx(5.0)
    routed = _cfg("openai_compatible", "z-ai/glm-5.3", base_url=OPENROUTER)
    assert routed.rates("z-ai/glm-5.3") == Rates(1.4, 4.4, 0.14)
    assert _cfg("openai_compatible", "llama3.1:8b").rates("llama3.1:8b") is None


def test_the_current_defaults_are_priced():
    for model in ("claude-opus-5-5", "gpt-6.1-sol", "gemini-3.8-flash"):
        assert curated_rates(model) is not None


# ---------- the live catalog: which server it prices ----------


def test_the_catalog_parser_reads_per_token_prices_per_million():
    parsed = prices.parse(CATALOG)
    assert parsed["anthropic/claude-opus-5.5"] == OPUS
    assert parsed["google/gemini-3.8-flash"] == Rates(0.75, 3.75, 0.075, None)
    assert parsed["vendor/free"] == Rates(0.0, 0.0)
    assert "openrouter/auto" not in parsed
    assert "vendor/half" not in parsed
    assert "vendor/odd" not in parsed
    assert not any(len(k) > 120 for k in parsed)
    assert prices.parse({"data": "x"}) == {}
    assert prices.parse([]) == {}


@pytest.mark.parametrize(
    ("provider", "model", "base_url", "ids"),
    [
        ("anthropic", "claude-opus-5-5", "", ["anthropic/claude-opus-5.5"]),
        ("anthropic", "claude-haiku-4-5-20251001", "", ["anthropic/claude-haiku-4.5"]),
        ("anthropic", "claude-opus-5", "", ["anthropic/claude-opus-5"]),
        ("anthropic", "claude-fable-5-1", "", ["anthropic/claude-fable-5.1"]),
        ("openai", "gpt-6.1-sol", "", ["openai/gpt-6.1-sol"]),
        (
            "openai",
            "gpt-4o-2024-08-06",
            "",
            ["openai/gpt-4o-2024-08-06", "openai/gpt-4o"],
        ),
        ("google", "models/gemini-3.8-flash", "", ["google/gemini-3.8-flash"]),
        ("openai_compatible", "z-ai/glm-5.3", OPENROUTER, ["z-ai/glm-5.3"]),
        ("openai_compatible", "z-ai/glm-5.3", "https://api.orcarouter.ai/v1", []),
        (
            "openai_compatible",
            "openai/gpt-oss-120b",
            OPENROUTER,
            ["openai/gpt-oss-120b"],
        ),
        ("openai_compatible", "openai/gpt-oss-120b", "http://vllm:8000/v1", []),
        ("openai_compatible", "gpt-oss-20b", "http://localhost:1234/v1", []),
        ("openai_compatible", "google/gemma-3-27b-it", "http://vllm:8000/v1", []),
        ("openai_compatible", "gemma-3-12b-it", "http://localhost:1234/v1", []),
        ("openai_compatible", "qwen/qwen3-8b", "http://localhost:1234/v1", []),
        ("openai_compatible", "llama3.1:8b", "http://ollama:11434/v1", []),
        (
            "openai_compatible",
            "claude-sonnet-5-5",
            "http://litellm:4000/v1",
            ["anthropic/claude-sonnet-5.5"],
        ),
        (
            "openai_compatible",
            "anthropic/claude-opus-5-5",
            "https://llm.corp.example/v1",
            ["anthropic/claude-opus-5.5"],
        ),
        (
            "openai_compatible",
            "google/gemini-3.8-flash",
            "https://llm.corp.example/v1",
            ["google/gemini-3.8-flash"],
        ),
        ("openai_compatible", "gpt-6-luna", "", ["openai/gpt-6-luna"]),
        ("anthropic", "  ", "", []),
    ],
)
def test_a_server_takes_live_prices_for_closed_models_or_from_openrouter(
    provider, model, base_url, ids
):
    assert prices.catalog_ids(provider, model, base_url) == ids


def test_bare_openai_ids_follow_the_chat_pattern():
    assert any(pattern is OPENAI_CHAT_ID for pattern, _ in prices._CLOSED)
    for model in ("gpt-6-luna", "chatgpt-6o-latest", "o4-mini"):
        assert openai_chat_model(model)
        assert prices.catalog_ids("openai_compatible", model) == [f"openai/{model}"]


def test_a_self_hosted_model_is_never_priced_from_the_live_catalog(price_cache):
    _seed(price_cache)
    vllm = _cfg(
        "openai_compatible", "openai/gpt-oss-120b", base_url="http://vllm:8000/v1"
    )
    assert vllm.charge(Usage(10_000, 2_000)).usd is None
    listing = list_models(
        vllm,
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200, json={"data": [{"id": "openai/gpt-oss-120b"}]}
            )
        ),
    )
    assert listing.models[0].input_per_mtok is None
    routed = _cfg("openai_compatible", "openai/gpt-oss-120b", base_url=OPENROUTER)
    assert routed.charge(Usage(10_000, 2_000)).usd == pytest.approx(
        (10_000 * 0.037 + 2_000 * 0.17) / 1e6
    )


def test_a_reader_never_downloads(monkeypatch):
    monkeypatch.setattr(prices, "download", lambda: pytest.fail("a reader downloaded"))
    assert prices.lookup("openai", "gpt-5.5") is None
    assert _cfg("openai", "gpt-5.5").charge(Usage(10, 1)).usd is None


def test_a_process_keeps_its_copy_when_the_shared_one_is_gone(price_cache, monkeypatch):
    _seed(price_cache)
    prices.forget()
    assert prices.lookup("openai", "gpt-5.5") is not None
    price_cache.delete(prices.CACHE_KEY)
    monkeypatch.setattr(prices, "MEMO_SECONDS", -1)
    assert prices.lookup("openai", "gpt-5.5") == Rates(5.0, 30.0, 0.5, None)


def test_a_shared_copy_that_cannot_be_read_is_no_price(monkeypatch):
    class Down:
        def get(self, _key):
            msg = "redis down"
            raise ConnectionError(msg)

    monkeypatch.setattr(prices, "sync_client", Down)
    assert prices.lookup("google", "gemini-3.8-flash") is None


# ---------- the price list download ----------


def _serve(monkeypatch, handler) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def counted(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def make(**kwargs) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(counted),
            follow_redirects=kwargs["follow_redirects"],
        )

    monkeypatch.setattr(prices, "get_sync_client", make)
    return seen


def test_the_download_reads_the_catalog(monkeypatch):
    seen = _serve(monkeypatch, lambda _r: httpx.Response(200, content=BODY))
    assert REAL_DOWNLOAD() == BODY
    assert [str(r.url) for r in seen] == [prices.CATALOG_URL]
    assert len(prices.read(BODY)) == LISTED


def test_the_download_refuses_a_redirect_without_following_it(monkeypatch):
    seen = _serve(
        monkeypatch,
        lambda _r: httpx.Response(
            301, headers={"Location": "https://elsewhere.example/"}
        ),
    )
    with pytest.raises(ValueError, match="301"):
        REAL_DOWNLOAD()
    assert len(seen) == 1


@pytest.mark.parametrize("status", [404, 500, 503])
def test_the_download_refuses_an_error_status(monkeypatch, status):
    _serve(monkeypatch, lambda _r: httpx.Response(status, content=BODY))
    with pytest.raises(ValueError, match=str(status)):
        REAL_DOWNLOAD()


def test_the_download_refuses_a_body_past_the_cap(monkeypatch):
    monkeypatch.setattr(prices, "MAX_BYTES", 1_000)
    _serve(monkeypatch, lambda _r: httpx.Response(200, content=b"x" * 5_000))
    with pytest.raises(ValueError, match="exceeded"):
        REAL_DOWNLOAD()


@pytest.mark.parametrize(
    "body",
    [
        b'{"data": []}',
        b"<html>maintenance</html>",
        b'{"data": [{"id": "x", "pricing": {"prompt": "-1", "completion": "-1"}}]}',
    ],
)
def test_a_list_that_names_no_price_is_refused(body):
    with pytest.raises(ValueError, match=r"no prices|Expecting value"):
        prices.read(body)


# ---------- the price list as a dataset ----------


@pytest.fixture
async def price_table(session):
    yield session
    await session.rollback()
    await session.execute(delete(AiPrice))
    await session.execute(
        delete(ThreatFeed).where(ThreatFeed.kind == DatasetKind.AI_PRICES.value)
    )
    await session.commit()


async def _feed(session) -> ThreatFeed:
    session.expire_all()
    return (
        await session.execute(
            select(ThreatFeed).where(ThreatFeed.kind == DatasetKind.AI_PRICES.value)
        )
    ).scalar_one()


async def test_the_price_list_loads_into_its_table_and_is_shared(
    price_table, price_cache, monkeypatch
):
    monkeypatch.setattr(prices, "download", lambda: BODY)
    assert await price_table.run_sync(prices.load) == LISTED

    stored = await price_table.run_sync(prices.stored)
    assert stored["anthropic/claude-opus-5.5"] == OPUS
    feed = await _feed(price_table)
    assert (feed.status, feed.rows, feed.bytes) == (
        FeedStatus.READY.value,
        LISTED,
        len(BODY),
    )
    assert price_cache.ttl[prices.CACHE_KEY] is None
    prices.forget()
    assert prices.lookup("openai", "gpt-5.5") == Rates(5.0, 30.0, 0.5, None)

    listed = {d.kind: d for d in await DatasetService(price_table).list()}
    entry = listed[DatasetKind.AI_PRICES.value]
    assert (entry.status, entry.rows) == (FeedStatus.READY.value, LISTED)


async def test_a_load_another_process_holds_returns_at_once(
    price_table, engine, monkeypatch
):
    monkeypatch.setattr(prices, "download", lambda: pytest.fail("loaded twice"))
    key = locks.dataset(DatasetKind.AI_PRICES.value)
    async with engine.connect() as other:
        await other.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        try:
            started = time.monotonic()
            assert await price_table.run_sync(prices.load) is None
            assert time.monotonic() - started < 1
        finally:
            await other.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})


async def test_a_failed_load_keeps_the_stored_list_and_shares_it(
    price_table, price_cache, monkeypatch
):
    monkeypatch.setattr(prices, "download", lambda: BODY)
    await price_table.run_sync(prices.load)
    price_cache.delete(prices.CACHE_KEY)
    prices.forget()

    def down() -> bytes:
        msg = "price list answered 503"
        raise ValueError(msg)

    monkeypatch.setattr(prices, "download", down)
    with pytest.raises(ValueError, match="503"):
        await price_table.run_sync(prices.load)

    feed = await _feed(price_table)
    assert (feed.status, feed.error, feed.rows) == (
        FeedStatus.FAILED.value,
        "price list answered 503",
        LISTED,
    )
    assert len(await price_table.run_sync(prices.stored)) == LISTED
    assert prices.CACHE_KEY in price_cache.data


async def test_boot_shares_the_stored_list(price_table, price_cache, monkeypatch):
    assert await price_table.run_sync(prices.share) is False
    monkeypatch.setattr(prices, "download", lambda: BODY)
    await price_table.run_sync(prices.load)
    price_cache.data.clear()
    prices.forget()
    assert await price_table.run_sync(prices.share) is True
    assert prices.lookup("anthropic", "claude-opus-5-5") == OPUS


# ---------- converse: failures and Stop keep what was spent ----------


class _Stream:
    def __init__(self, step: dict):
        self.step = step
        self.current_message_snapshot = SimpleNamespace(usage=step.get("snapshot"))

    async def __aenter__(self):
        if self.step.get("refuse") is not None:
            raise self.step["refuse"]
        return self

    async def __aexit__(self, *_exc):
        return False

    @property
    def text_stream(self):
        return self._texts()

    async def _texts(self):
        for text_ in self.step.get("texts", []):
            yield text_
        if self.step.get("hang"):
            await asyncio.Event().wait()
        if self.step.get("error") is not None:
            raise self.step["error"]

    async def get_final_message(self):
        return self.step["final"]


def _fake_anthropic(monkeypatch, steps: list[dict]) -> None:
    import anthropic  # noqa: PLC0415

    script = iter(steps)
    messages = SimpleNamespace(stream=lambda **_k: _Stream(next(script)))
    monkeypatch.setattr(
        anthropic, "AsyncAnthropic", lambda **_k: SimpleNamespace(messages=messages)
    )


def _tool_round(inp: int, out: int, reads: int = 0) -> dict:
    return {
        "snapshot": _usage(inp, 1, reads),
        "texts": ["Looking. "],
        "final": SimpleNamespace(
            stop_reason="tool_use",
            usage=_usage(inp, out, reads),
            content=[
                SimpleNamespace(type="tool_use", name="query_assets", id="t1", input={})
            ],
        ),
    }


def _last_round(inp: int, out: int, geo: str | None = None) -> dict:
    return {
        "snapshot": _usage(inp, 1, geo=geo),
        "texts": ["Done."],
        "final": SimpleNamespace(
            stop_reason="end_turn", usage=_usage(inp, out, geo=geo), content=[]
        ),
    }


async def _tool(_name, _args):
    return "3 rows", True


def _ask(cfg: AIConfig, call_tool=_tool):
    return converse(
        cfg,
        system="s",
        messages=[{"role": "user", "content": "q"}],
        tools=[agent.AgentTool("query_assets", "Query", {"type": "object"})],
        call_tool=call_tool,
        task="ask",
        max_rounds=6,
    )


async def test_done_carries_the_charge_the_ledger_stored(book, monkeypatch):
    _fake_anthropic(monkeypatch, [_tool_round(1000, 40), _last_round(1200, 30)])
    events = [e async for e in _ask(_cfg())]
    done = events[-1]
    assert done.kind == DONE
    assert done.usage == Usage(2200, 70)
    assert done.charge.usd == pytest.approx(book[-1].priced().usd)
    assert (book[-1].ok, book[-1].rounds) == (True, 2)


async def test_us_only_inference_prices_every_round_of_an_answer(book, monkeypatch):
    _fake_anthropic(monkeypatch, [_last_round(1200, 30, geo="us")])
    events = [e async for e in _ask(_cfg())]
    expected = (1200 * 4.0 + 30 * 20.0) * 1.1 / 1e6
    assert events[-1].charge.usd == pytest.approx(expected)


async def test_a_refused_round_costs_nothing_beside_the_billed_ones(book, monkeypatch):
    refusal = {
        "snapshot": _usage(1100, 1),
        "final": SimpleNamespace(
            stop_reason="refusal",
            stop_details=SimpleNamespace(category="cyber"),
            usage=_usage(1100, 0),
            content=[],
        ),
    }
    _fake_anthropic(monkeypatch, [_tool_round(1000, 40), refusal])
    with pytest.raises(AIError, match=DECLINED):
        async for _ in _ask(_cfg()):
            pass
    rec = book[-1]
    assert (rec.ok, rec.usage.input_tokens, rec.usage.output_tokens) == (
        False,
        2100,
        40,
    )
    assert rec.priced().usd == pytest.approx((1000 * 4.0 + 40 * 20.0) / 1e6)


async def test_a_stream_cut_mid_round_keeps_its_tokens_and_is_unpriced(
    book, monkeypatch
):
    import anthropic  # noqa: PLC0415

    _fake_anthropic(
        monkeypatch,
        [
            _tool_round(800, 60, reads=200),
            {
                "snapshot": _usage(1500, 3),
                "texts": ["More"],
                "error": anthropic.APIConnectionError(request=_http_request()),
            },
        ],
    )
    with pytest.raises(AIError) as err:
        async for _ in _ask(_cfg()):
            pass

    assert err.value.usage.counts == (2500, 63, 200, 0)
    assert len(book) == 1
    rec = book[0]
    assert (rec.ok, rec.usage.counts, rec.rounds) == (False, (2500, 63, 200, 0), 2)
    assert rec.priced().usd is None


async def test_a_round_the_provider_turned_away_leaves_an_exact_cost(book, monkeypatch):
    import anthropic  # noqa: PLC0415
    import httpx2  # noqa: PLC0415

    overloaded = anthropic.OverloadedError(
        "Overloaded",
        response=httpx2.Response(529, request=_http_request()),
        body={"type": "error", "error": {"type": "overloaded_error"}},
    )
    _fake_anthropic(monkeypatch, [_tool_round(800, 60), {"refuse": overloaded}])
    with pytest.raises(AIError, match="529"):
        async for _ in _ask(_cfg()):
            pass
    assert book[-1].priced().usd == pytest.approx((800 * 4.0 + 60 * 20.0) / 1e6)


async def test_stop_mid_stream_keeps_the_tokens_and_is_unpriced(book, monkeypatch):
    _fake_anthropic(
        monkeypatch,
        [
            _tool_round(1000, 40),
            {"snapshot": _usage(1300, 2), "texts": ["Par"], "hang": True},
        ],
    )
    seen = asyncio.Event()

    async def consume():
        with ledger.source("thread"):
            async for event in _ask(_cfg()):
                if event.kind == TEXT and event.text == "Par":
                    seen.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(seen.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(book) == 1
    rec = book[0]
    assert (rec.ok, rec.error, rec.source.kind) == (False, STOPPED, "thread")
    assert rec.usage.counts == (2300, 42, 0, 0)
    assert rec.priced().usd is None


async def test_stop_between_rounds_keeps_an_exact_cost(book, monkeypatch):
    _fake_anthropic(monkeypatch, [_tool_round(1000, 40)])
    calling = asyncio.Event()

    async def slow_tool(_name, _args):
        calling.set()
        await asyncio.Event().wait()

    async def consume():
        async for _ in _ask(_cfg(), slow_tool):
            pass

    task = asyncio.create_task(consume())
    await asyncio.wait_for(calling.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    rec = book[-1]
    assert (rec.error, rec.usage) == (STOPPED, Usage(1000, 40))
    assert rec.priced().usd == pytest.approx((1000 * 4.0 + 40 * 20.0) / 1e6)


async def test_closing_the_stream_keeps_the_partial_round(book, monkeypatch):
    _fake_anthropic(
        monkeypatch,
        [{"snapshot": _usage(900, 4), "texts": ["One", "Two"], "hang": True}],
    )
    stream = _ask(_cfg())
    first = await anext(stream)
    assert first.text == "One"
    await stream.aclose()
    assert len(book) == 1
    assert (book[0].error, book[0].usage.counts) == (STOPPED, (900, 4, 0, 0))
    assert book[0].priced().usd is None


def _round_body(prompt: int, completion: int, *, tool: bool, **usage) -> dict:
    message = {"content": "" if tool else "Done."}
    if tool:
        message["tool_calls"] = [
            {"id": "c1", "function": {"name": "query_assets", "arguments": "{}"}}
        ]
    return {
        "choices": [{"message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            **usage,
        },
    }


async def test_an_openai_failure_carries_every_round(book, monkeypatch):
    bodies = iter(
        [
            _round_body(
                1000, 40, tool=True, prompt_tokens_details={"cached_tokens": 600}
            ),
        ]
    )

    def post(*_a, **_k):
        try:
            return next(bodies)
        except StopIteration:
            raise client.http_error(
                500,
                json.dumps(
                    {
                        "error": {"message": "upstream"},
                        "usage": {"prompt_tokens": 1100, "completion_tokens": 0},
                    }
                ),
            ) from None

    monkeypatch.setattr(agent, "post_json", post)
    with pytest.raises(AIError) as err:
        async for _ in _ask(_cfg("openai", "gpt-6.1-sol")):
            pass
    spent = Usage(2100, 40, 600, 0)
    assert err.value.usage == spent
    assert (book[-1].ok, book[-1].usage) == (False, spent)
    expected = (1500 * 2.0 + 600 * 0.1 + 40 * 10.0) / 1e6
    assert book[-1].priced().usd == pytest.approx(expected)


async def test_an_openai_round_that_timed_out_is_unpriced(book, monkeypatch):
    bodies = iter([_round_body(1000, 40, tool=True)])

    def post(*_a, **_k):
        try:
            return next(bodies)
        except StopIteration:
            msg = "The provider did not respond: timed out"
            raise AIError(msg) from None

    monkeypatch.setattr(agent, "post_json", post)
    with pytest.raises(AIError):
        async for _ in _ask(_cfg("openai", "gpt-6.1-sol")):
            pass
    assert book[-1].usage.counts == (1000, 40, 0, 0)
    assert book[-1].priced().usd is None


async def test_a_router_cost_reaches_the_answer(book, monkeypatch):
    bodies = iter(
        [
            _round_body(1000, 40, tool=True, cost=0.002),
            _round_body(1100, 60, tool=False, cost="0.003"),
        ]
    )
    monkeypatch.setattr(agent, "post_json", lambda *_a, **_k: next(bodies))
    events = [e async for e in _ask(_cfg("openai_compatible", "z-ai/glm-5.3"))]
    done = events[-1]
    assert done.charge.usd == pytest.approx(0.005)
    assert done.charge.source == "provider"
    assert book[-1].priced().usd == pytest.approx(0.005)


async def test_stop_during_an_openai_round_waits_for_its_usage(book, monkeypatch):
    entered, release, written = threading.Event(), threading.Event(), threading.Event()

    def post(*_a, **_k):
        entered.set()
        release.wait(5)
        return _round_body(700, 20, tool=False)

    def write(rec: ledger.CallRecord) -> None:
        book.append(rec)
        written.set()

    monkeypatch.setattr(agent, "post_json", post)
    ledger.register(write)

    async def consume():
        async for _ in _ask(_cfg("openai", "gpt-6.1-sol")):
            pass

    task = asyncio.create_task(consume())
    assert await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert book == []

    release.set()
    assert await asyncio.to_thread(written.wait, 5)
    assert len(book) == 1
    assert (book[0].error, book[0].usage) == (STOPPED, Usage(700, 20))
    assert book[0].priced().usd == pytest.approx((700 * 2.0 + 20 * 10.0) / 1e6)


# ---------- the report receipt ----------


def test_the_report_receipt_counts_every_call_the_ledger_writes(book, monkeypatch):
    monkeypatch.setattr(cache, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(cache, "store", lambda *_a, **_k: None)
    receipt = AIUsage()
    task = AITask.EXECUTIVE_SUMMARY.value

    monkeypatch.setattr(client, "_anthropic", lambda *_a, **_k: ("", Usage(3600, 1400)))
    assert (
        cache.narrate(None, _cfg(), task=task, system="s", prompt="a", usage=receipt)
        is None
    )

    def refuse(*_a, **_k):
        raise AIError(DECLINED, usage=Usage(500, 3))

    monkeypatch.setattr(client, "_anthropic", refuse)
    assert (
        cache.narrate(None, _cfg(), task=task, system="s", prompt="b", usage=receipt)
        is None
    )

    assert receipt.calls == len(book) == 2
    assert receipt.input_tokens == sum(r.usage.input_tokens for r in book) == 4100
    assert receipt.output_tokens == sum(r.usage.output_tokens for r in book) == 1403
    assert len(receipt.failures) == 1


# ---------- stored rates ----------


@pytest.fixture
def flush_only(estate, monkeypatch):
    monkeypatch.setattr(estate.session, "commit", estate.session.flush)
    monkeypatch.setattr(
        estate.session.sync_session, "commit", estate.session.sync_session.flush
    )
    return estate.session


def _stored(row) -> tuple:
    return (
        row.input_per_mtok,
        row.output_per_mtok,
        row.cache_read_per_mtok,
        row.cache_write_per_mtok,
    )


async def _saved(session, connection) -> tuple:
    return _stored(await session.get(AiConnection, connection.id))


async def test_saving_stores_the_listed_price(
    estate, flush_only, price_cache, monkeypatch
):
    _seed(price_cache)
    own = {"z-ai/glm-5.3": Rates(1.26, 3.96, 0.2)}
    monkeypatch.setattr(client, "listed_rates", lambda cfg: own.get(cfg.model))
    service = AiSettingsService(flush_only)
    curated = await service.create_connection(
        AiConnectionCreate(
            provider="anthropic", api_key="sk-ant-x", model="claude-opus-5-5"
        )
    )
    live = await service.create_connection(
        AiConnectionCreate(provider="openai", api_key="sk-x", model="gpt-5.5")
    )
    listed = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="https://router.example/v1",
            model="z-ai/glm-5.3",
        )
    )
    manual = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="http://ollama:11434/v1",
            model="llama3.1:8b",
        )
    )
    vllm = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="http://vllm:8000/v1",
            model="openai/gpt-oss-120b",
        )
    )

    assert await _saved(flush_only, curated) == (4.0, 20.0, 0.2, 5.0)
    assert await _saved(flush_only, live) == (5.0, 30.0, 0.5, None)
    assert await _saved(flush_only, listed) == (1.26, 3.96, 0.2, None)
    assert await _saved(flush_only, manual) == (None, None, None, None)
    assert await _saved(flush_only, vllm) == (None, None, None, None)


async def test_a_save_that_keeps_the_model_keeps_the_stored_price(
    estate, flush_only, monkeypatch
):
    monkeypatch.setattr(client, "listed_rates", lambda _cfg: Rates(1.26, 3.96, 0.234))
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="https://api.orcarouter.ai/v1",
            model="z-ai/glm-5.3",
        )
    )

    monkeypatch.setattr(
        client, "listed_rates", lambda cfg: Rates(1.0, 3.0, 0.1) if cfg.model else None
    )
    renamed = await service.update_connection(
        routed.id, AiConnectionUpdate(name="Orca")
    )
    assert await _saved(flush_only, renamed) == (1.26, 3.96, 0.234, None)

    moved = await service.update_connection(
        routed.id, AiConnectionUpdate(model="z-ai/glm-5.4")
    )
    assert await _saved(flush_only, moved) == (1.0, 3.0, 0.1, None)


async def test_an_unread_server_list_keeps_the_stored_price(price_cache, monkeypatch):
    _seed(price_cache)
    row = AiConnection(
        name="orca",
        provider="openai_compatible",
        base_url="https://api.orcarouter.ai/v1",
        model="claude-opus-5-5",
        input_per_mtok=6.0,
        output_per_mtok=30.0,
        cache_read_per_mtok=0.6,
    )

    def down(*_a):
        msg = "The provider did not respond: timed out"
        raise AIError(msg)

    monkeypatch.setattr(client, "_listed", down)
    assert rates.lookup(row) is None
    assert rates.apply(row, rates.lookup(row)) is False
    assert rates.stored(row) == Rates(6.0, 30.0, 0.6)

    monkeypatch.setattr(
        client, "_listed", lambda *_a: [client._Listed("claude-opus-5-5")]
    )
    assert rates.lookup(row) == OPUS
    row.model = "z-ai/glm-5.3"
    assert rates.lookup(row) is None


async def test_use_answers_from_the_stored_row(estate, flush_only, monkeypatch):
    monkeypatch.setattr(client, "listed_rates", lambda _cfg: Rates(1.26, 3.96))
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="https://router.example/v1",
            api_key="sk-or-x",
            model="z-ai/glm-5.3",
        )
    )
    monkeypatch.setattr(
        client, "listed_rates", lambda _cfg: pytest.fail("Use read the server's list")
    )
    used = await service.use_connection(routed.id)
    assert used.in_use
    assert await _saved(flush_only, used) == (1.26, 3.96, None, None)


async def test_test_reprices_only_once_the_server_answered(
    estate, flush_only, monkeypatch
):
    reads: list[str] = []

    def listed(cfg):
        reads.append(cfg.model)
        return Rates(1.5, 4.0, 0.15)

    answered = {"ok": False}

    def ping(cfg, **_k):
        if not answered["ok"]:
            msg = "Provider returned 503."
            raise AIError(msg, usage=Usage())
        return SimpleNamespace(model=cfg.model, latency_ms=1)

    monkeypatch.setattr(client, "listed_rates", lambda _cfg: Rates(1.26, 3.96))
    monkeypatch.setattr(ai_settings, "complete", ping)
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="https://router.example/v1",
            api_key="sk-or-x",
            model="z-ai/glm-5.3",
        )
    )
    monkeypatch.setattr(client, "listed_rates", listed)

    failed = await service.test_connection(routed.id)
    assert (failed.success, reads) == (False, [])

    answered["ok"] = True
    passed = await service.test_connection(routed.id)
    row = await flush_only.get(AiConnection, routed.id)
    assert (passed.success, reads) == (True, ["z-ai/glm-5.3"])
    assert rates.stored(row) == Rates(1.5, 4.0, 0.15)


async def test_the_daily_job_refreshes_every_stored_price(
    estate, flush_only, monkeypatch, price_cache
):
    _seed(price_cache)
    monkeypatch.setattr(prices, "load", lambda _s: LISTED)
    monkeypatch.setattr(client, "listed_rates", lambda _cfg: None)
    stale = AiConnection(
        name="old",
        provider="anthropic",
        model="claude-opus-5-5",
        input_per_mtok=5.0,
        output_per_mtok=25.0,
    )
    live = AiConnection(name="live", provider="openai", model="gpt-5.5")
    local = AiConnection(
        name="local",
        provider="openai_compatible",
        base_url="http://ollama:11434/v1",
        model="llama3.1:8b",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
    )
    flush_only.add_all([stale, live, local])
    await flush_only.flush()

    result = await flush_only.run_sync(rates.refresh_all)

    assert (result["models"], result["repriced"]) == (LISTED, 2)
    assert rates.stored(stale) == OPUS
    assert rates.stored(live) == Rates(5.0, 30.0, 0.5, None)
    assert rates.stored(local) == Rates(0.0, 0.0)


async def test_the_listing_fills_prices_from_the_live_catalog(price_cache):
    _seed(price_cache)
    listed = list_models(
        _cfg("openai", ""),
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200,
                json={
                    "data": [{"id": "gpt-5.5"}, {"id": "gpt-6.1-sol"}, {"id": "gpt-9"}]
                },
            )
        ),
    )
    by_id = {m.id: m for m in listed.models}
    assert (by_id["gpt-5.5"].input_per_mtok, by_id["gpt-5.5"].output_per_mtok) == (
        5.0,
        30.0,
    )
    assert by_id["gpt-5.5"].cache_read_per_mtok == 0.5
    assert by_id["gpt-6.1-sol"].input_per_mtok == 2.0
    assert by_id["gpt-9"].input_per_mtok is None


# ---------- usage read off the ledger ----------


async def test_usage_counts_cached_tokens_and_unpriced_calls(estate):
    now = utc_now()

    def row(**kw) -> AiCall:
        return AiCall(
            at=now, task="ask", feature="ask", provider="anthropic", model="m", **kw
        )

    estate.session.add_all(
        [
            row(input_tokens=1000, cache_read_tokens=600, cost_usd=0.002),
            row(input_tokens=10, output_tokens=2),
            row(cached=True, cost_usd=0.0),
            row(ok=False, cost_usd=0.0),
        ]
    )
    await estate.session.flush()
    usage = await AiSettingsService(estate.session).usage()
    ask = next(f for f in usage.by_feature if f.feature == "ask")
    assert (ask.cache_read_tokens, ask.unpriced) == (600, 1)
    assert (usage.unpriced, usage.cost_usd) == (1, pytest.approx(0.002))
    page = await AiSettingsService(estate.session).calls(10)
    assert {c.cache_read_tokens for c in page.items} == {0, 600}
