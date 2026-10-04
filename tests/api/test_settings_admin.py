from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from fastapi import HTTPException, Response

from app.api.v1.ai import ai_status, list_connections
from app.api.v1.api_keys import list_providers, reveal_api_key
from app.api.v1.users import create_user, delete_user, update_user
from app.services import ai_settings
from app.services.ai_settings import AiSettingsService, _clean_base_url
from app.services.instance_settings import InstanceSettingsService, _check_window
from app.services.proxy import ProxyService, _summarize
from app.services.scan_context import ScanContextService
from shared.definitions.retention import KEEP_FOREVER, SCAN_RETENTION_DAYS
from shared.enums.api_key import APIProvider
from shared.models.ai import (
    AiConnection,
    AiConnectionCreate,
    AiConnectionUpdate,
    AiTestRequest,
)
from shared.models.api_key import APIKey, APIKeyUpdate
from shared.models.instance_settings import InstanceSettingsRead, InstanceSettingsUpdate
from shared.models.notification_channel import NotificationChannel
from shared.models.project import Project
from shared.models.proxy import Proxy, ProxyEndpoint, ProxyTestResult
from shared.models.scan_context import ScanContext, ScanContextCreate
from shared.models.user import User, UserAdminCreate, UserAdminUpdate
from shared.services.ai import client
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.notifier import _RECORD_DELIVERY, _delivery_rows
from shared.services.proxy_resolve import resolve_proxy_url
from shared.utils.crypto import encrypt_secret, try_decrypt

pytestmark = pytest.mark.api

STRONG = "Vq7#mT9!pLx2@wRz"


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _admin(estate) -> User:
    return await estate.session.get(User, estate.user_id)


async def _member(session, *, superuser: bool = False) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"ops{tag}",
        email=f"ops{tag}@test.local",
        hashed_password="x",
        is_superuser=superuser,
    )
    session.add(user)
    await session.flush()
    return user


def _proxy(name: str, endpoints: list[dict], *, default: bool, created_by) -> Proxy:
    return Proxy(
        name=name,
        is_active=True,
        is_default=default,
        endpoints_encrypted=encrypt_secret(json.dumps(endpoints)),
        endpoint_count=len(endpoints),
        created_by=created_by,
    )


# ---------- users ----------


async def test_an_admin_creates_an_account_with_a_role(estate, flush_only):
    tag = uuid.uuid4().hex[:8]
    user = await create_user(
        UserAdminCreate(
            email=f"New{tag}@Test.local",
            username=f"new{tag}",
            password=STRONG,
            is_superuser=True,
        ),
        session=flush_only,
        current_user=await _admin(estate),
    )
    assert user.is_superuser
    assert user.email == f"new{tag}@test.local"


async def test_a_taken_username_is_refused(estate, flush_only):
    taken = await _member(flush_only)
    with pytest.raises(HTTPException) as err:
        await create_user(
            UserAdminCreate(
                email="other@test.local", username=taken.username, password=STRONG
            ),
            session=flush_only,
            current_user=await _admin(estate),
        )
    assert err.value.status_code == 409


async def test_the_signed_in_account_cannot_disable_itself(estate, flush_only):
    admin = await _admin(estate)
    with pytest.raises(HTTPException) as err:
        await update_user(
            admin.id,
            UserAdminUpdate(is_active=False),
            session=flush_only,
            current_user=admin,
        )
    assert err.value.status_code == 400


async def test_an_admin_disables_and_demotes_another_account(estate, flush_only):
    other = await _member(flush_only, superuser=True)
    updated = await update_user(
        other.id,
        UserAdminUpdate(is_active=False, is_superuser=False),
        session=flush_only,
        current_user=await _admin(estate),
    )
    assert not updated.is_active
    assert not updated.is_superuser


async def test_an_account_that_owns_records_is_not_deleted(estate, flush_only):
    owner = await _member(flush_only)
    flush_only.add(
        Project(
            id=uuid.uuid4(),
            name="Owned",
            slug=f"owned-{owner.id.hex[:8]}",
            created_by=owner.id,
        )
    )
    await flush_only.flush()
    with pytest.raises(HTTPException) as err:
        await delete_user(
            str(owner.id), session=flush_only, current_user=await _admin(estate)
        )
    assert err.value.status_code == 409
    assert "Disable the account" in err.value.detail


# ---------- api keys ----------


async def test_a_key_test_is_stored_and_a_new_key_clears_it(estate, flush_only):
    key = APIKey(provider=APIProvider.VIEWDNS, key_value=encrypt_secret("first"))
    flush_only.add(key)
    await flush_only.flush()
    service = APIKeyService(flush_only)

    await service.record_test(key, True, "API Key is valid.")
    read = service._to_read(key)
    assert read.last_test_ok is True
    assert read.last_test_message == "API Key is valid."

    read = await service.update_key(str(key.id), APIKeyUpdate(key_value="second"))
    assert read.last_test_at is None
    assert read.last_test_ok is None


async def test_providers_state_which_keys_can_be_tested(estate, flush_only):
    providers = {
        p.provider: p
        for p in await list_providers(
            _current_user=await _admin(estate), service=APIKeyService(flush_only)
        )
    }
    assert providers[APIProvider.VIEWDNS].testable
    assert providers[APIProvider.TELEGRAM].testable
    assert not providers[APIProvider.CHAOS].testable


async def test_a_revealed_key_is_not_cached(estate, flush_only):
    key = APIKey(provider=APIProvider.VIEWDNS, key_value=encrypt_secret("plain"))
    flush_only.add(key)
    await flush_only.flush()
    response = Response()

    body = await reveal_api_key(
        str(key.id),
        _current_user=await _admin(estate),
        service=APIKeyService(flush_only),
        response=response,
    )

    assert body == {"key_value": "plain"}
    assert response.headers["Cache-Control"] == "no-store"


# ---------- proxies ----------


async def test_a_scan_without_a_context_uses_the_default_proxy(estate, flush_only):
    fallback = _proxy(
        "fallback",
        [{"scheme": "http", "host": "10.0.0.9", "port": 3128}],
        default=True,
        created_by=estate.user_id,
    )
    chosen = _proxy(
        "chosen",
        [{"scheme": "socks5", "host": "10.0.0.7", "port": 1080}],
        default=False,
        created_by=estate.user_id,
    )
    flush_only.add_all([fallback, chosen])
    await flush_only.flush()
    service = ProxyService(flush_only)

    assert await service.scan_proxy_url(None) == "http://10.0.0.9:3128"
    assert (
        await service.scan_proxy_url(SimpleNamespace(proxy_id=chosen.id))
        == "socks5://10.0.0.7:1080"
    )
    assert await service.scan_proxy_url(SimpleNamespace(proxy_id=None)) is None


async def test_a_new_context_takes_the_default_proxy_unless_one_is_named(
    estate, flush_only
):
    fallback = _proxy(
        "fallback",
        [{"scheme": "http", "host": "10.0.0.9", "port": 3128}],
        default=True,
        created_by=estate.user_id,
    )
    flush_only.add(fallback)
    await flush_only.flush()
    contexts = ScanContextService(flush_only)

    implied = await contexts.create(
        estate.project_id, estate.user_id, ScanContextCreate(name="implied")
    )
    direct = await contexts.create(
        estate.project_id,
        estate.user_id,
        ScanContextCreate(name="direct", proxy_id=None),
    )

    assert implied.proxy_id == fallback.id
    assert direct.proxy_id is None


def test_a_pool_hands_each_scan_one_of_its_endpoints():
    pool = SimpleNamespace(
        name="pool",
        is_active=True,
        endpoints_encrypted=encrypt_secret(
            json.dumps(
                [
                    {"scheme": "http", "host": "10.0.0.1", "port": 8080},
                    {"scheme": "http", "host": "10.0.0.2", "port": 8080},
                    {"scheme": "http", "host": "2001:db8::5", "port": 8080},
                ]
            )
        ),
    )
    urls = {resolve_proxy_url(pool) for _ in range(60)}
    assert urls <= {
        "http://10.0.0.1:8080",
        "http://10.0.0.2:8080",
        "http://[2001:db8::5]:8080",
    }
    assert len(urls) > 1


def test_a_pool_test_names_the_endpoint_that_failed():
    endpoints = [
        ProxyEndpoint(scheme="http", host="10.0.0.1", port=8080),
        ProxyEndpoint(scheme="http", host="10.0.0.2", port=8080),
    ]
    result = _summarize(
        endpoints,
        [
            ProxyTestResult(success=True, message="Proxy reachable.", latency_ms=90),
            ProxyTestResult(success=False, message="Connection failed: refused"),
        ],
    )
    assert not result.success
    assert result.message.startswith("1 of 2 endpoints carried the request.")
    assert "10.0.0.2:8080" in result.message


async def test_a_deleted_proxy_leaves_its_contexts_direct(estate, flush_only):
    doomed = _proxy(
        "doomed",
        [{"scheme": "http", "host": "10.0.0.3", "port": 8080}],
        default=False,
        created_by=estate.user_id,
    )
    flush_only.add(doomed)
    await flush_only.flush()
    context = ScanContext(
        project_id=estate.project_id,
        created_by=estate.user_id,
        name="through doomed",
        proxy_id=doomed.id,
    )
    flush_only.add(context)
    await flush_only.flush()

    listed = {p.id: p for p in await ProxyService(flush_only).list()}
    assert listed[doomed.id].contexts == 1

    await ProxyService(flush_only).delete(doomed.id)
    await flush_only.refresh(context)
    assert context.proxy_id is None


# ---------- notifications ----------


async def test_a_delivery_is_recorded_on_the_channel(estate, session):
    channel = NotificationChannel(
        name="soc", provider="slack", config_encrypted="", created_by=estate.user_id
    )
    session.add(channel)
    await session.flush()
    await session.execute(
        _RECORD_DELIVERY, _delivery_rows([(channel.id, False, "HTTP 500.")])
    )
    row = (
        await session.execute(
            sa.select(
                NotificationChannel.last_sent_ok, NotificationChannel.last_sent_message
            ).where(NotificationChannel.id == channel.id)
        )
    ).one()
    assert row == (False, "HTTP 500.")


# ---------- general ----------


def test_a_retention_window_must_be_an_offered_one():
    _check_window("Scan history", KEEP_FOREVER, SCAN_RETENTION_DAYS)
    with pytest.raises(HTTPException) as err:
        _check_window("Scan history", 45, SCAN_RETENTION_DAYS)
    assert err.value.status_code == 400


async def test_a_blank_instance_name_is_refused(estate, flush_only):
    with pytest.raises(HTTPException) as err:
        await InstanceSettingsService(flush_only).update(
            InstanceSettingsUpdate(instance_name="   ")
        )
    assert err.value.status_code == 400


async def test_general_settings_do_not_write_the_ai_connection(estate, flush_only):
    service = InstanceSettingsService(flush_only)
    settings = await service.get_or_create()
    stored = await _stored_ai(flush_only)
    settings.ai_features = {"ask": True}
    await flush_only.flush()

    await service.update(
        InstanceSettingsUpdate.model_validate(
            {
                "instance_name": "ops",
                "ai_provider": "openai",
                "ai_api_key": "sk-new",
                "ai_connection_id": str(uuid.uuid4()),
                "ai_features": {"ask": False},
            }
        )
    )

    assert settings.ai_connection_id == stored.id
    assert settings.ai_features == {"ask": True}
    assert "ai_features" not in InstanceSettingsRead.model_fields
    assert "ai_connection_id" not in InstanceSettingsRead.model_fields


# ---------- ai ----------


@pytest.fixture(autouse=True)
def unlisted(monkeypatch):
    monkeypatch.setattr(client, "listed_rates", lambda _cfg: None)


async def _stored_ai(session):
    return await AiSettingsService(session).create_connection(
        AiConnectionCreate(
            provider="openai_compatible",
            base_url="https://llm.example.com/v1",
            api_key="stored",
            model="m",
        )
    )


async def test_an_ai_test_sends_the_stored_key_to_the_stored_server_alone(
    estate, flush_only, monkeypatch
):
    stored = await _stored_ai(flush_only)
    sent: list[tuple[str, str]] = []

    def fake_complete(cfg, **_k):
        sent.append((cfg.base_url, cfg.api_key))
        return SimpleNamespace(model=cfg.model, latency_ms=1)

    monkeypatch.setattr(ai_settings, "complete", fake_complete)
    service = AiSettingsService(flush_only)

    await service.test(AiTestRequest(connection_id=stored.id, model="m"))
    await service.test(
        AiTestRequest(
            connection_id=stored.id, base_url="https://collector.example/v1", model="m"
        )
    )
    await service.test(
        AiTestRequest(
            provider="openai_compatible",
            base_url="https://llm.example.com/v1",
            model="m",
        )
    )
    refused = await service.test(
        AiTestRequest(connection_id=stored.id, provider="openai", model="m")
    )

    assert sent == [
        ("https://llm.example.com/v1", "stored"),
        ("https://collector.example/v1", ""),
        ("https://llm.example.com/v1", ""),
    ]
    assert not refused.success


async def test_moving_the_ai_server_drops_the_stored_key(estate, flush_only):
    stored = await _stored_ai(flush_only)
    service = AiSettingsService(flush_only)
    row = await flush_only.get(AiConnection, stored.id)

    with pytest.raises(HTTPException) as err:
        await service.update_connection(
            stored.id, AiConnectionUpdate(provider="openai")
        )
    assert err.value.status_code == 400
    assert try_decrypt(row.api_key_encrypted) == "stored"

    await service.update_connection(stored.id, AiConnectionUpdate(model="m2"))
    assert try_decrypt(row.api_key_encrypted) == "stored"

    await service.update_connection(
        stored.id, AiConnectionUpdate(base_url="https://collector.example/v1")
    )
    assert row.api_key_encrypted is None


@pytest.mark.parametrize(
    "url",
    ["https://svc:pass@llm.example.com/v1", "https://llm.example.com/v1?key=k"],
)
def test_a_server_url_with_credentials_or_a_query_is_refused(url):
    with pytest.raises(HTTPException) as err:
        _clean_base_url(url)
    assert err.value.status_code == 400


async def test_only_an_admin_reads_the_ai_server(estate, flush_only):
    await _stored_ai(flush_only)
    await AiSettingsService(flush_only).create_connection(
        AiConnectionCreate(
            provider="anthropic", api_key="sk-ant-0123456789", workspace_id="ws"
        )
    )

    member = await ai_status(SimpleNamespace(is_superuser=False), flush_only)
    admin = await ai_status(SimpleNamespace(is_superuser=True), flush_only)
    listed = await list_connections(SimpleNamespace(is_superuser=False), flush_only)
    full = await list_connections(SimpleNamespace(is_superuser=True), flush_only)

    assert (member.base_url, member.workspace_id) == (None, None)
    assert admin.base_url == "https://llm.example.com/v1"
    assert [(c.base_url, c.workspace_id) for c in listed] == [(None, None)] * 2
    assert [(c.base_url, c.workspace_id) for c in full] == [
        ("https://llm.example.com/v1", None),
        (None, "ws"),
    ]
