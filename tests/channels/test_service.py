"""Pairing approval, capability caps, revocation and the command catalog through the service."""

from __future__ import annotations

import uuid

import pytest

from channels import pairing
from channels import service as channel_service
from channels.models import ChannelChatUpdate, ChannelSettingsUpdate, PairingApprove
from channels.service import ChannelConfigError, ChannelService
from mcp import telemetry
from mcp.models import McpCeiling
from shared.definitions.channels import ChannelKind, ChatState
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.utils.crypto import encrypt_secret

pytestmark = pytest.mark.channels

CHANNEL = ChannelKind.TELEGRAM.value


@pytest.fixture
def quiet(monkeypatch):
    """No Redis pairing state, no Telegram calls."""

    async def take(_channel, code):
        return {
            "code": code,
            "external_id": "424242",
            "display": "@operator",
            "username": "operator",
            "first_name": "Op",
        }

    async def notify(*_args, **_kwargs):
        return None

    monkeypatch.setattr(pairing, "take", take)
    monkeypatch.setattr(channel_service.telegram_driver, "notify", notify)


async def test_approve_pairs_the_chat_to_an_account(estate, quiet):
    service = ChannelService(estate.session, CHANNEL)
    chat = await service.approve(
        "H7K2-Q9XZ",
        PairingApprove(
            user_id=estate.user_id,
            project_id=estate.project_id,
            capabilities=["read", "plan"],
        ),
        estate.user_id,
    )
    assert chat.state == ChatState.ACTIVE.value
    assert chat.external_id == "424242"
    assert chat.capabilities == ["read", "plan"]
    assert chat.project_id == estate.project_id
    assert chat.totp_enabled is False
    assert chat.effective_capabilities == ["read"]


async def test_approve_refuses_a_capability_above_the_ceiling(estate, quiet):
    service = ChannelService(estate.session, CHANNEL)
    with pytest.raises(ChannelConfigError, match="Launch is switched off"):
        await service.approve(
            "H7K2-Q9XZ",
            PairingApprove(
                user_id=estate.user_id,
                project_id=estate.project_id,
                capabilities=["read", "launch"],
            ),
            estate.user_id,
        )


async def test_approve_refuses_an_unknown_account_or_project(estate, quiet):
    service = ChannelService(estate.session, CHANNEL)
    with pytest.raises(ChannelConfigError, match="account"):
        await service.approve(
            "H7K2-Q9XZ",
            PairingApprove(user_id=uuid.uuid4(), project_id=estate.project_id),
            estate.user_id,
        )
    with pytest.raises(ChannelConfigError, match="project"):
        await service.approve(
            "H7K2-Q9XZ",
            PairingApprove(user_id=estate.user_id, project_id=uuid.uuid4()),
            estate.user_id,
        )


async def test_lowering_the_ceiling_narrows_every_chat(estate, quiet):
    service = ChannelService(estate.session, CHANNEL)
    await service.update(
        ChannelSettingsUpdate(ceiling=McpCeiling(plan=True, write=True, launch=False)),
        estate.user_id,
    )
    chat = await service.approve(
        "H7K2-Q9XZ",
        PairingApprove(
            user_id=estate.user_id,
            project_id=estate.project_id,
            capabilities=["read", "plan", "write"],
        ),
        estate.user_id,
    )
    assert chat.capabilities == ["read", "plan", "write"]
    await service.update(
        ChannelSettingsUpdate(ceiling=McpCeiling(plan=True, write=False, launch=False)),
        estate.user_id,
    )
    rows = await service.chats()
    assert rows[0].capabilities == ["read", "plan"]


async def test_revoke_and_delete(estate, quiet):
    service = ChannelService(estate.session, CHANNEL)
    chat = await service.approve(
        "H7K2-Q9XZ",
        PairingApprove(user_id=estate.user_id, project_id=estate.project_id),
        estate.user_id,
    )
    revoked = await service.revoke_chat(chat.id)
    assert revoked.state == ChatState.REVOKED.value
    with pytest.raises(ChannelConfigError, match="active"):
        await service.update_chat(chat.id, ChannelChatUpdate(capabilities=["read"]))
    await service.delete_chat(chat.id)
    assert await service.chats() == []


async def test_the_api_key_is_the_bot_token_and_never_returned(estate):
    token = "1234567890:AAFxYz0123456789abcdefghijklmnopqrst"
    estate.session.add(
        APIKey(provider=APIProvider.TELEGRAM, key_value=encrypt_secret(token))
    )
    await estate.session.flush()
    service = ChannelService(estate.session, CHANNEL)
    status = await service.status()
    assert status.configured is True
    assert status.secret_masked == "1234567890:••••••••"
    assert token not in status.model_dump_json()


async def test_starting_needs_a_token(estate):
    service = ChannelService(estate.session, CHANNEL)
    with pytest.raises(ChannelConfigError, match="API key"):
        await service.update(ChannelSettingsUpdate(enabled=True), estate.user_id)


def test_the_command_catalog_is_served():
    rows = ChannelService.commands()
    names = {row.name for row in rows}
    assert {"help", "scan", "progress", "vulns", "whois"} <= names
    scan = next(r for r in rows if r.name == "scan")
    assert scan.usage.startswith("/scan <target>")
    assert scan.group == "scans"
    assert any(a.name == "target" and a.required for a in scan.args)


async def test_a_chat_call_is_found_behind_newer_calls_from_other_clients(estate):
    mark = uuid.uuid4().hex[:8]
    record = telemetry.CallRecord(
        token_id=uuid.uuid4(),
        token_name="chat",
        client=CHANNEL,
        tool=mark,
        ok=True,
        duration_ms=1,
    )
    await telemetry.record(record)
    for _ in range(20):
        await telemetry.record(
            telemetry.CallRecord(
                token_id=uuid.uuid4(),
                token_name="agent",
                client="http",
                tool="query_assets",
                ok=True,
                duration_ms=1,
            )
        )

    rows = await ChannelService(estate.session, CHANNEL).calls(limit=5)

    assert any(row.tool == mark for row in rows), "a cut before the filter hides it"
