"""Saved AI providers: one in use, keys kept, models read from the provider."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.deps import get_current_superuser
from app.api.v1 import onboarding as onboarding_routes
from app.api.v1.ai import router
from app.services import ai_settings
from app.services.ai_settings import AiSettingsService
from app.services.ask.service import availability
from app.services.instance_settings import InstanceSettingsService
from shared.definitions.ai import Rates
from shared.models.ai import (
    AiConnection,
    AiConnectionCreate,
    AiConnectionUpdate,
    AiModelList,
    AiModelsRequest,
    AiOnboarding,
    AiSettingsUpdate,
    AiTestRequest,
)
from shared.services.ai import client, ledger
from shared.services.ai.client import list_models
from shared.services.ai.config import AIConfig, load_config, load_config_async
from shared.services.scan_resolve import MASK
from shared.utils.crypto import try_decrypt

pytestmark = pytest.mark.api

ANTHROPIC_KEY = "sk-ant-api03-0123456789abcdef"
ROUTER_KEY = "sk-or-v1-fedcba9876543210"


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


@pytest.fixture(autouse=True)
def unlisted(monkeypatch):
    monkeypatch.setattr(client, "listed_rates", lambda _cfg: None)


def _anthropic(**kw) -> AiConnectionCreate:
    return AiConnectionCreate(provider="anthropic", api_key=ANTHROPIC_KEY, **kw)


def _router(**kw) -> AiConnectionCreate:
    return AiConnectionCreate(
        provider="openai_compatible",
        api_key=ROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        model="qwen/qwen3-coder",
        **kw,
    )


async def _settings(session):
    return await InstanceSettingsService(session).get_or_create()


async def _stored_key(session, connection_id: uuid.UUID) -> str | None:
    row = await session.get(AiConnection, connection_id)
    return try_decrypt(row.api_key_encrypted)


# ---------- create, list, mask ----------


async def test_a_saved_provider_is_listed_with_its_key_masked(estate, flush_only):
    service = AiSettingsService(flush_only)
    created = await service.create_connection(_anthropic(workspace_id="ws-1"))

    assert created.key_masked == f"{MASK}cdef"
    assert ANTHROPIC_KEY not in created.model_dump_json()
    assert created.model == "claude-opus-5-5"
    assert await _stored_key(flush_only, created.id) == ANTHROPIC_KEY

    admin = await service.connections(full=True)
    member = await service.connections(full=False)
    assert [c.name for c in admin] == ["Anthropic"]
    assert admin[0].workspace_id == "ws-1"
    assert (member[0].workspace_id, member[0].key_masked) == (None, f"{MASK}cdef")


async def test_a_default_name_takes_the_label_or_the_server_host(estate, flush_only):
    service = AiSettingsService(flush_only)
    first = await service.create_connection(_anthropic())
    second = await service.create_connection(_anthropic())
    routed = await service.create_connection(_router())

    assert (first.name, second.name, routed.name) == (
        "Anthropic",
        "Anthropic 2",
        "openrouter.ai",
    )
    with pytest.raises(HTTPException) as err:
        await service.create_connection(_anthropic(name="anthropic"))
    assert err.value.status_code == 409


async def test_a_provider_needs_its_key_its_server_and_a_model(estate, flush_only):
    service = AiSettingsService(flush_only)
    for body in (
        AiConnectionCreate(provider="anthropic"),
        AiConnectionCreate(provider="openai_compatible", model="m"),
        AiConnectionCreate(
            provider="openai_compatible", base_url="http://ollama:11434/v1"
        ),
        AiConnectionCreate(provider="nope", api_key="k"),
    ):
        with pytest.raises(HTTPException) as err:
            await service.create_connection(body)
        assert err.value.status_code == 400

    local = await service.create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="http://ollama:11434/v1/",
            model="llama3.1",
        )
    )
    assert (local.name, local.key_masked, local.base_url) == (
        "ollama",
        None,
        "http://ollama:11434/v1",
    )


# ---------- in use ----------


async def test_the_first_provider_is_in_use_and_one_click_moves_it(estate, flush_only):
    service = AiSettingsService(flush_only)
    first = await service.create_connection(_anthropic())
    second = await service.create_connection(_router())
    third = await service.create_connection(_anthropic(use=True))

    assert (first.in_use, second.in_use, third.in_use) == (True, False, True)
    assert (await _settings(flush_only)).ai_connection_id == third.id

    used = await service.use_connection(second.id)
    listed = {c.name: c.in_use for c in await service.connections(full=True)}

    assert used.in_use
    assert listed == {"Anthropic": False, "openrouter.ai": True, "Anthropic 2": False}
    assert await _stored_key(flush_only, first.id) == ANTHROPIC_KEY


async def test_status_reports_the_provider_in_use(estate, flush_only):
    service = AiSettingsService(flush_only)
    await service.create_connection(_anthropic())
    routed = await service.create_connection(_router(use=True))

    member = await service.status(full=False)
    admin = await service.status(full=True)

    assert (admin.connection_id, admin.provider, admin.model) == (
        routed.id,
        "openai_compatible",
        "qwen/qwen3-coder",
    )
    assert admin.configured
    assert "fast_model" not in admin.model_dump()
    assert admin.key_masked == f"{MASK}3210"
    assert admin.base_url == "https://openrouter.ai/api/v1"
    assert member.base_url is None


async def test_deleting_the_provider_in_use_leaves_none_in_use(estate, flush_only):
    service = AiSettingsService(flush_only)
    first = await service.create_connection(_anthropic())
    second = await service.create_connection(_router())

    await service.delete_connection(first.id)
    status = await service.status(full=True)
    cfg = await load_config_async(flush_only)

    assert (await _settings(flush_only)).ai_connection_id is None
    assert (status.connection_id, status.provider, status.configured) == (
        None,
        None,
        False,
    )
    assert [c.id for c in await service.connections(full=True)] == [second.id]
    assert cfg is not None
    assert not cfg.available
    with pytest.raises(HTTPException) as err:
        await service.update(AiSettingsUpdate(enabled=True))
    assert err.value.status_code == 400

    again = await service.create_connection(_anthropic())
    assert again.in_use


async def test_load_config_resolves_the_provider_in_use(estate, flush_only):
    service = AiSettingsService(flush_only)
    await service.create_connection(_anthropic())
    routed = await service.create_connection(
        _router(input_per_mtok=1.26, output_per_mtok=3.96)
    )
    await service.update(AiSettingsUpdate(enabled=True, features={"ask": False}))

    cfg = await load_config_async(flush_only)
    assert (cfg.provider, cfg.api_key, cfg.model) == (
        "anthropic",
        ANTHROPIC_KEY,
        "claude-opus-5-5",
    )
    assert cfg.available
    assert not cfg.allows("ask")

    await service.use_connection(routed.id)
    synced = await flush_only.run_sync(load_config)

    assert (synced.provider, synced.api_key, synced.base_url) == (
        "openai_compatible",
        ROUTER_KEY,
        "https://openrouter.ai/api/v1",
    )
    assert synced.model == "qwen/qwen3-coder"
    assert synced.listed_price("qwen/qwen3-coder") == Rates(1.26, 3.96)
    assert synced.listed_price("other/model") is None
    assert synced.workspace == ""


# ---------- merge on update ----------


async def test_a_masked_key_keeps_the_stored_key(estate, flush_only):
    service = AiSettingsService(flush_only)
    created = await service.create_connection(_anthropic())

    await service.update_connection(
        created.id,
        AiConnectionUpdate(api_key=created.key_masked, model="claude-sonnet-5"),
    )
    await service.update_connection(created.id, AiConnectionUpdate(name="Team"))

    row = await flush_only.get(AiConnection, created.id)
    assert (row.name, row.model) == ("Team", "claude-sonnet-5")
    assert try_decrypt(row.api_key_encrypted) == ANTHROPIC_KEY
    assert MASK not in row.api_key_encrypted


async def test_moving_the_server_drops_the_stored_key(estate, flush_only):
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(_router())

    with pytest.raises(HTTPException) as err:
        await service.update_connection(
            routed.id, AiConnectionUpdate(provider="openai")
        )
    assert err.value.status_code == 400
    assert await _stored_key(flush_only, routed.id) == ROUTER_KEY

    await service.update_connection(
        routed.id, AiConnectionUpdate(base_url="https://collector.example/v1")
    )
    assert await _stored_key(flush_only, routed.id) is None

    moved = await service.update_connection(
        routed.id, AiConnectionUpdate(provider="anthropic", api_key=ANTHROPIC_KEY)
    )
    assert (moved.provider, moved.model, moved.base_url) == (
        "anthropic",
        "claude-opus-5-5",
        None,
    )
    assert await _stored_key(flush_only, routed.id) == ANTHROPIC_KEY


async def test_a_test_result_is_stored_on_the_provider(estate, flush_only, monkeypatch):
    sent: list[AIConfig] = []

    def fake_complete(cfg, **_k):
        sent.append(cfg)
        return SimpleNamespace(model=cfg.model, latency_ms=3)

    monkeypatch.setattr(ai_settings, "complete", fake_complete)
    service = AiSettingsService(flush_only)
    created = await service.create_connection(_anthropic(workspace_id="ws-1"))

    result = await service.test_connection(created.id, estate.user_id)
    row = await flush_only.get(AiConnection, created.id)

    assert result.success
    assert result.message.startswith("Anthropic answered in")
    assert (sent[0].api_key, sent[0].workspace) == (ANTHROPIC_KEY, "ws-1")
    assert (row.last_test_ok, row.last_test_message) == (True, result.message)
    assert row.last_test_at is not None

    await service.update_connection(created.id, AiConnectionUpdate(model="other"))
    assert row.last_test_ok is None


@pytest.mark.parametrize(
    "change",
    [
        {"model": "claude-sonnet-5"},
        {"api_key": "sk-ant-api03-another-key-0000"},
        {"workspace_id": "ws-2"},
        {"provider": "openai", "api_key": "sk-proj-0123456789"},
    ],
)
async def test_a_change_to_what_was_tested_clears_the_test(
    estate, flush_only, monkeypatch, change
):
    monkeypatch.setattr(
        ai_settings,
        "complete",
        lambda cfg, **_k: SimpleNamespace(model=cfg.model, latency_ms=1),
    )
    service = AiSettingsService(flush_only)
    created = await service.create_connection(_anthropic(workspace_id="ws-1"))
    await service.test_connection(created.id)

    renamed = await service.update_connection(
        created.id, AiConnectionUpdate(name="Team", api_key=created.key_masked)
    )
    assert renamed.last_test_ok is True

    changed = await service.update_connection(created.id, AiConnectionUpdate(**change))
    assert (changed.last_test_at, changed.last_test_ok) == (None, None)


async def test_a_moved_server_clears_the_test(estate, flush_only, monkeypatch):
    monkeypatch.setattr(
        ai_settings,
        "complete",
        lambda cfg, **_k: SimpleNamespace(model=cfg.model, latency_ms=1),
    )
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(_router())
    await service.test_connection(routed.id)

    moved = await service.update_connection(
        routed.id,
        AiConnectionUpdate(base_url="https://collector.example/v1", api_key="k2"),
    )
    assert moved.last_test_ok is None


# ---------- listed prices ----------


async def test_a_listed_price_is_kept_with_its_model(estate, flush_only):
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(
        _router(input_per_mtok=0.3, output_per_mtok=1.2)
    )
    assert (routed.input_per_mtok, routed.output_per_mtok) == (0.3, 1.2)

    renamed = await service.update_connection(
        routed.id, AiConnectionUpdate(name="Router")
    )
    assert (renamed.input_per_mtok, renamed.output_per_mtok) == (0.3, 1.2)

    repriced = await service.update_connection(
        routed.id, AiConnectionUpdate(input_per_mtok=0.4, output_per_mtok=1.6)
    )
    assert (repriced.input_per_mtok, repriced.output_per_mtok) == (0.4, 1.6)

    unlisted = await service.update_connection(
        routed.id, AiConnectionUpdate(model="vendor/unlisted")
    )
    assert (unlisted.input_per_mtok, unlisted.output_per_mtok) == (None, None)

    half = await service.update_connection(
        routed.id, AiConnectionUpdate(model="z-ai/glm-5.3", input_per_mtok=1.26)
    )
    assert (half.input_per_mtok, half.output_per_mtok) == (None, None)


def test_a_listed_price_must_be_a_price():
    for value in (-1, 10_001):
        with pytest.raises(ValidationError):
            AiConnectionUpdate(input_per_mtok=value, output_per_mtok=1.0)
    with pytest.raises(ValidationError):
        AiConnectionCreate(provider="anthropic", fast_model="claude-haiku-4-5")


async def test_a_draft_test_uses_the_stored_key_on_its_own_server(
    estate, flush_only, monkeypatch
):
    sent: list[tuple[str, str]] = []

    def fake_complete(cfg, **_k):
        sent.append((cfg.base_url, cfg.api_key))
        return SimpleNamespace(model=cfg.model, latency_ms=1)

    monkeypatch.setattr(ai_settings, "complete", fake_complete)
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(_router())

    await service.test(AiTestRequest(connection_id=routed.id))
    await service.test(
        AiTestRequest(connection_id=routed.id, base_url="https://collector.example/v1")
    )
    refused = await service.test(
        AiTestRequest(connection_id=routed.id, provider="openai", model="m")
    )

    assert sent == [
        ("https://openrouter.ai/api/v1", ROUTER_KEY),
        ("https://collector.example/v1", ""),
    ]
    assert not refused.success


# ---------- model listing through the service ----------


async def test_models_use_the_stored_key_only_on_its_own_server(
    estate, flush_only, monkeypatch
):
    seen: list[AIConfig] = []

    def fake_list(cfg, **_k):
        seen.append(cfg)
        return AiModelList()

    monkeypatch.setattr(ai_settings, "list_models", fake_list)
    service = AiSettingsService(flush_only)
    routed = await service.create_connection(_router())
    anthropic = await service.create_connection(_anthropic())

    await service.models(AiModelsRequest(connection_id=routed.id))
    await service.models(
        AiModelsRequest(
            connection_id=routed.id, base_url="https://collector.example/v1"
        )
    )
    other = await service.models(
        AiModelsRequest(connection_id=anthropic.id, provider="openai")
    )
    bad = await service.models(
        AiModelsRequest(provider="openai_compatible", base_url="ftp://host/v1")
    )

    assert [(c.base_url, c.api_key) for c in seen] == [
        ("https://openrouter.ai/api/v1", ROUTER_KEY),
        ("https://collector.example/v1", ""),
    ]
    assert other.error == "Enter the API key for this server."
    assert bad.error == "Server URL must start with http:// or https://."


# ---------- list_models per provider ----------


def _cfg(provider: str, key: str = "k-secret-value", **kw) -> AIConfig:
    return AIConfig(provider=provider, api_key=key, model="", features={}, **kw)


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def test_anthropic_models_page_through_and_lead_with_the_catalog():
    requests: list[httpx.Request] = []
    pages = [
        {
            "data": [
                {"id": "claude-3-haiku-20240307", "display_name": "Claude Haiku 3"},
                {"id": "claude-opus-5-5", "display_name": "Claude Opus 5.5 (new)"},
            ],
            "has_more": True,
            "last_id": "claude-opus-5-5",
        },
        {
            "data": [
                {"id": "claude-haiku-4-5", "display_name": "Claude Haiku 4.5"},
                {"id": "claude-2.1", "display_name": "Claude 2.1"},
            ],
            "has_more": False,
            "last_id": "claude-2.1",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=pages[len(requests) - 1])

    listed = list_models(
        _cfg("anthropic", workspace="ws-1"), transport=_transport(handler)
    )

    assert listed.error is None
    assert [m.id for m in listed.models] == [
        "claude-opus-5-5",
        "claude-haiku-4-5",
        "claude-2.1",
        "claude-3-haiku-20240307",
    ]
    assert listed.models[0].label == "Claude Opus 5.5"
    assert listed.models[0].input_per_mtok == 4.0
    assert listed.models[0].cache_read_per_mtok == 0.2
    assert [m.recommended for m in listed.models] == [True, True, False, False]
    assert str(requests[0].url) == "https://api.anthropic.com/v1/models?limit=1000"
    assert requests[1].url.params["after_id"] == "claude-opus-5-5"
    assert requests[0].headers["x-api-key"] == "k-secret-value"
    assert requests[0].headers["anthropic-version"] == "2023-06-01"
    assert requests[0].headers["anthropic-workspace-id"] == "ws-1"


def test_a_dated_snapshot_lists_as_its_model():
    def listing(ids):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": i} for i in ids], "has_more": False}
            )

        return list_models(_cfg("anthropic"), transport=_transport(handler)).models

    alone = listing(["claude-haiku-4-5-20251001", "claude-opus-5-5"])
    both = listing(["claude-haiku-4-5-20251001", "claude-haiku-4-5"])

    snapshot = next(m for m in alone if m.id == "claude-haiku-4-5-20251001")
    assert (snapshot.label, snapshot.recommended) == ("Claude Haiku 4.5", True)
    assert (snapshot.input_per_mtok, snapshot.output_per_mtok) == (1.0, 5.0)
    assert [m.id for m in alone] == ["claude-opus-5-5", "claude-haiku-4-5-20251001"]
    assert [(m.id, m.recommended) for m in both] == [
        ("claude-haiku-4-5", True),
        ("claude-haiku-4-5-20251001", False),
    ]


def test_openai_models_keep_the_chat_families():
    ids = [
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
        "gpt-4o-mini-tts",
        "gpt-4o-transcribe",
        "gpt-4o-realtime-preview",
        "gpt-4o-audio-preview",
        "gpt-image-1",
        "text-embedding-3-small",
        "whisper-1",
        "dall-e-3",
        "omni-moderation-latest",
        "babbage-002",
        "gpt-3.5-turbo-instruct",
        "gpt-5",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer k-secret-value"
        return httpx.Response(200, json={"data": [{"id": i} for i in ids]})

    listed = list_models(_cfg("openai"), transport=_transport(handler))

    assert [m.id for m in listed.models] == [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-5",
        "o3-mini",
    ]


def test_google_models_need_generate_content_and_keep_the_key_in_a_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "k-secret-value" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "k-secret-value"
        if "pageToken" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-3.8-flash",
                            "displayName": "Gemini Flash",
                            "supportedGenerationMethods": [
                                "generateContent",
                                "countTokens",
                            ],
                        },
                        {
                            "name": "models/text-embedding-004",
                            "displayName": "Embedding",
                            "supportedGenerationMethods": ["embedContent"],
                        },
                    ],
                    "nextPageToken": "p2",
                },
            )
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemma-3-27b-it",
                        "displayName": "Gemma 3 27B",
                        "supportedGenerationMethods": ["generateContent"],
                    }
                ]
            },
        )

    listed = list_models(_cfg("google"), transport=_transport(handler))

    assert [(m.id, m.label) for m in listed.models] == [
        ("gemini-3.8-flash", "Gemini 3.8 Flash"),
        ("gemma-3-27b-it", "Gemma 3 27B"),
    ]


def test_openrouter_pricing_is_read_per_million_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://openrouter.ai/api/v1/models"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "qwen/qwen3-coder",
                        "name": "Qwen: Qwen3 Coder",
                        "pricing": {"prompt": "0.0000003", "completion": "0.0000012"},
                    },
                    {
                        "id": "openrouter/auto",
                        "name": "Auto Router",
                        "pricing": {"prompt": "-1", "completion": "-1"},
                    },
                    {"id": "meta-llama/llama-3.1-8b-instruct:free", "pricing": {}},
                ]
            },
        )

    listed = list_models(
        _cfg("openai_compatible", base_url="https://openrouter.ai/api/v1/"),
        transport=_transport(handler),
    )
    by_id = {m.id: m for m in listed.models}

    assert (
        by_id["qwen/qwen3-coder"].input_per_mtok,
        by_id["qwen/qwen3-coder"].output_per_mtok,
    ) == (0.3, 1.2)
    assert by_id["qwen/qwen3-coder"].label == "Qwen: Qwen3 Coder"
    assert by_id["openrouter/auto"].input_per_mtok is None
    assert by_id["meta-llama/llama-3.1-8b-instruct:free"].label == (
        "meta-llama/llama-3.1-8b-instruct:free"
    )


def test_a_local_server_is_listed_without_a_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(
            200, json={"object": "list", "data": [{"id": "llama3.1:8b"}]}
        )

    listed = list_models(
        _cfg("openai_compatible", key="", base_url="http://ollama:11434/v1"),
        transport=_transport(handler),
    )

    assert [m.id for m in listed.models] == ["llama3.1:8b"]


def _echo_key(request: httpx.Request) -> httpx.Response:
    key = request.headers["authorization"].removeprefix("Bearer ")
    return httpx.Response(
        401, text=json.dumps({"error": f"bad key {key} for {request.url}?k=1"})
    )


def _refuse(_request: httpx.Request) -> httpx.Response:
    msg = "refused https://svc:pw@llm.internal/v1?api_key=k-secret-value"
    raise httpx.ConnectError(msg)


@pytest.mark.parametrize("handler", [_echo_key, _refuse])
def test_a_listing_failure_is_an_error_with_no_key_and_no_credentials(handler):
    listed = list_models(
        _cfg("openai_compatible", base_url="https://llm.internal/v1"),
        transport=_transport(handler),
    )

    assert listed.models == []
    assert listed.error
    assert "k-secret-value" not in listed.error
    assert "svc:pw" not in listed.error


def test_a_redirect_or_a_page_that_is_not_json_is_refused():
    redirect = list_models(
        _cfg("openai_compatible", base_url="https://llm.internal/v1"),
        transport=_transport(
            lambda _r: httpx.Response(302, headers={"location": "https://evil/"})
        ),
    )
    page = list_models(
        _cfg("openai_compatible", base_url="https://llm.internal/v1"),
        transport=_transport(lambda _r: httpx.Response(200, text="<html>")),
    )

    assert "redirect" in redirect.error
    assert "not JSON" in page.error


def test_listing_models_writes_no_ledger_row():
    rows: list[ledger.CallRecord] = []
    ledger.register(rows.append)
    try:
        list_models(
            _cfg("openai"),
            transport=_transport(lambda _r: httpx.Response(200, json={"data": []})),
        )
        list_models(
            _cfg("openai"), transport=_transport(lambda _r: httpx.Response(500))
        )
    finally:
        ledger.register(None)
    assert rows == []


def test_ask_takes_a_keyless_local_server_and_names_a_missing_provider():
    local = AIConfig(
        provider="openai_compatible",
        api_key="",
        model="llama3.1",
        features={"ask": True},
        base_url="http://ollama:11434/v1",
    )

    assert availability(local) is None
    assert availability(_cfg("", key="")) == "No AI provider is in use."


# ---------- onboarding ----------


async def test_onboarding_saves_one_provider_and_updates_it(estate, flush_only):
    service = AiSettingsService(flush_only)
    first = await service.onboard(
        AiOnboarding(
            enabled=True,
            provider="anthropic",
            api_key=ANTHROPIC_KEY,
            features={"asset_judgement": True},
        )
    )
    again = await service.onboard(
        AiOnboarding(enabled=True, provider="anthropic", model="claude-sonnet-5")
    )
    rows = await service.connections(full=True)
    settings = await _settings(flush_only)

    assert first.connection.id == again.connection.id
    assert [(c.model, c.in_use) for c in rows] == [("claude-sonnet-5", True)]
    assert settings.ai_enabled
    assert again.features["asset_judgement"]
    assert await _stored_key(flush_only, rows[0].id) == ANTHROPIC_KEY

    progress = onboarding_routes.OnboardingProgress(
        current_step=4, state={"mode": "bug_bounty", "ai_connection_id": "forged"}
    )
    await onboarding_routes.update_progress(
        progress,
        SimpleNamespace(is_superuser=True),
        flush_only,
        InstanceSettingsService(flush_only),
    )
    assert (await service.onboarding()).connection.id == first.connection.id

    routed = await service.onboard(
        AiOnboarding(
            enabled=True,
            provider="openai_compatible",
            base_url="https://openrouter.ai/api/v1",
            api_key=ROUTER_KEY,
            model="qwen/qwen3-coder",
            input_per_mtok=0.3,
            output_per_mtok=1.2,
        )
    )
    assert (routed.connection.input_per_mtok, routed.connection.output_per_mtok) == (
        0.3,
        1.2,
    )
    kept = await service.onboard(AiOnboarding(enabled=True))
    assert kept.connection.input_per_mtok == 0.3

    off = await service.onboard(AiOnboarding(enabled=False))
    assert not off.enabled


# ---------- gates ----------

_WRITES = {
    ("POST", "/ai/connections"),
    ("PATCH", "/ai/connections/{connection_id}"),
    ("DELETE", "/ai/connections/{connection_id}"),
    ("POST", "/ai/connections/{connection_id}/use"),
    ("POST", "/ai/connections/{connection_id}/test"),
    ("POST", "/ai/models"),
    ("POST", "/ai/test"),
    ("PATCH", "/ai/settings"),
    ("DELETE", "/ai/cache"),
}


def _gated(route) -> bool:
    return get_current_superuser in {d.call for d in route.dependant.dependencies}


def test_writes_and_model_listing_are_superuser_only():
    routes = {
        (method, route.path): route
        for route in router.routes
        for method in route.methods
    }
    assert {key for key, route in routes.items() if _gated(route)} == _WRITES
    assert not _gated(routes[("GET", "/ai/connections")])
    assert not _gated(routes[("GET", "/ai/status")])
