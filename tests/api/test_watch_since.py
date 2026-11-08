from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.api.deps import get_current_active_user
from app.api.v1 import bounty_programs
from app.core.database import get_session
from shared.models.watch import WatchHostCounts

pytestmark = pytest.mark.api


class _Watches:
    def __init__(self) -> None:
        self.since: datetime | None = None

    async def host_counts(self, _watch_id, _project_id, since):
        self.since = since
        return WatchHostCounts()


async def _allowed(*_args, **_kwargs) -> None:
    return None


@pytest.fixture
def watches(monkeypatch) -> _Watches:
    monkeypatch.setattr(bounty_programs, "require_capability", _allowed)
    return _Watches()


def _client(watches: _Watches) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(bounty_programs.router)
    app.dependency_overrides[get_current_active_user] = lambda: object()
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[bounty_programs.get_watches] = lambda: watches
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def _counts(watches: _Watches, since: str) -> int:
    async with _client(watches) as client:
        response = await client.get(
            f"/bounty-programs/watches/{uuid.uuid4()}/hosts/counts",
            params={"project_id": str(uuid.uuid4()), "since": since},
        )
    return response.status_code


@pytest.mark.parametrize(
    "since",
    ["2026-11-01T00:00:00", "2026-11-01", "2026-11-01T05:30:00+05:30"],
)
async def test_since_reaches_the_service_as_utc(watches, since):
    assert await _counts(watches, since) == 200
    assert watches.since == datetime(2026, 11, 1, tzinfo=UTC)
    assert watches.since.tzinfo is UTC


async def test_since_before_the_first_utc_instant_is_refused(watches):
    assert await _counts(watches, "0001-01-01T00:00:00+05:00") == 422
