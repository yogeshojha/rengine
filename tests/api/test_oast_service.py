from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.services.instance_settings import InstanceSettingsService
from app.services.oast import OastService
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.models.oast import OastUpdate
from shared.utils.crypto import encrypt_secret

pytestmark = pytest.mark.api


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _seed(session, server: str | None) -> OastService:
    row = await InstanceSettingsService(session).get_or_create()
    row.oast_server = server
    await session.execute(
        sa.delete(APIKey).where(APIKey.provider == APIProvider.INTERACTSH)
    )
    session.add(
        APIKey(provider=APIProvider.INTERACTSH, key_value=encrypt_secret("tok"))
    )
    await session.flush()
    return OastService(session)


async def test_moving_the_server_deletes_its_token(flush_only):
    service = await _seed(flush_only, "oast.one.example")
    read = await service.update(OastUpdate(server="oast.two.example"))
    assert read.server == "oast.two.example"
    assert read.token_set is False


async def test_the_same_server_keeps_its_token(flush_only):
    service = await _seed(flush_only, "oast.one.example")
    read = await service.update(OastUpdate(server="HTTPS://OAST.one.example/"))
    assert read.token_set is True


async def test_a_first_server_keeps_the_token_saved_with_it(flush_only):
    service = await _seed(flush_only, None)
    read = await service.update(OastUpdate(server="oast.one.example"))
    assert read.token_set is True


async def test_an_update_without_a_server_keeps_the_token(flush_only):
    service = await _seed(flush_only, "oast.one.example")
    read = await service.update(OastUpdate(wait_seconds=30))
    assert read.token_set is True
